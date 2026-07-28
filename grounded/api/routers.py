"""API routers: economics (cost), reviews (list + trace), and the HITL queue.

They read the in-process EventLog and ApprovalQueue (the production dashboard would read the
Tiger continuous aggregates and truth tables instead — same shapes). The lightweight dashboard
at ``/`` is a single self-contained page; a full Next.js app is the production target.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from grounded.hitl import ApprovalQueue, HumanDecision
from grounded.observability import EventLog


class DecideBody(BaseModel):
    decision: str  # "approve" | "reject"
    reviewer: str
    note: str = ""


class FeedbackBody(BaseModel):
    useful: bool
    note: str = ""


class DisputeBody(BaseModel):
    rule_id: str
    reason: str


def _ticket(t) -> dict:
    return {"review_id": t.review_id, "mode": t.mode, "status": t.status.value,
            "escalated": t.escalated, "reason": t.reason, "n_findings": t.n_findings,
            "reviewer": t.reviewer, "disputes": t.disputes, "feedback": t.feedback}


def build_api_router(events: EventLog, queue: ApprovalQueue) -> APIRouter:
    r = APIRouter(prefix="/api")

    @r.get("/economics/summary")
    def economics_summary() -> dict:
        return {"total_cost_usd": events.total_cost(), "by_agent": events.cost_by_agent(),
                "n_reviews": len(events.review_ids()), "n_events": len(events.all())}

    @r.get("/reviews")
    def list_reviews() -> list[dict]:
        return [_ticket(t) for t in queue.all()]

    @r.get("/reviews/{review_id}/trace")
    def review_trace(review_id: str) -> dict:
        rows = events.for_review(review_id)
        if not rows:
            raise HTTPException(404, "no such review")
        return {"review_id": review_id, "events": [asdict(e) for e in rows]}

    @r.get("/hitl/pending")
    def hitl_pending() -> list[dict]:
        return [_ticket(t) for t in queue.pending()]

    @r.post("/hitl/{review_id}/decide")
    def hitl_decide(review_id: str, body: DecideBody) -> dict:
        try:
            decision = HumanDecision(body.decision)
        except ValueError:
            raise HTTPException(400, "decision must be 'approve' or 'reject'")
        try:
            return _ticket(queue.decide(review_id, decision, body.reviewer, body.note))
        except (KeyError, ValueError) as exc:
            raise HTTPException(404, str(exc))

    @r.post("/hitl/{review_id}/feedback")
    def hitl_feedback(review_id: str, body: FeedbackBody) -> dict:
        try:
            return _ticket(queue.feedback(review_id, body.useful, body.note))
        except KeyError as exc:
            raise HTTPException(404, str(exc))

    @r.post("/hitl/{review_id}/dispute")
    def hitl_dispute(review_id: str, body: DisputeBody) -> dict:
        try:
            return _ticket(queue.dispute(review_id, body.rule_id, body.reason))
        except KeyError as exc:
            raise HTTPException(404, str(exc))

    return r


def dashboard_router() -> APIRouter:
    r = APIRouter()

    @r.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return _DASHBOARD_HTML

    return r


_DASHBOARD_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>grounded-pr-review-agent</title>
<style>
 :root{color-scheme:light dark}
 body{font:14px/1.5 system-ui,sans-serif;margin:0;padding:24px;max-width:900px;margin:auto}
 h1{font-size:20px} h2{font-size:15px;margin:24px 0 8px;color:#888}
 .cards{display:flex;gap:12px;flex-wrap:wrap}
 .card{border:1px solid #8884;border-radius:10px;padding:14px 18px;min-width:130px}
 .card .n{font-size:24px;font-weight:600}
 table{width:100%;border-collapse:collapse;font-size:13px}
 td,th{text-align:left;padding:6px 8px;border-bottom:1px solid #8883}
 .pill{padding:1px 8px;border-radius:999px;font-size:11px;border:1px solid #8886}
 .pending{color:#c60} .auto_posted{color:#090} .approved{color:#090} .rejected{color:#c00}
 button{font:inherit;padding:3px 10px;border-radius:6px;border:1px solid #8886;cursor:pointer;background:transparent}
 .muted{color:#888}
</style></head><body>
<h1>grounded &middot; PR review agent</h1>
<div class="cards" id="cards"></div>
<h2>Human-in-the-loop queue</h2>
<table id="queue"><thead><tr><th>Review</th><th>Mode</th><th>Status</th><th>Findings</th><th>Reason</th><th></th></tr></thead><tbody></tbody></table>
<p class="muted" id="empty">No reviews yet. POST a signed payload to <code>/webhook/github</code> to see one here.</p>
<script>
async function j(u,o){const r=await fetch(u,o);return r.json()}
async function refresh(){
 const s=await j('/api/economics/summary');
 document.getElementById('cards').innerHTML=
   card('Reviews',s.n_reviews)+card('Events',s.n_events)+card('Cost','$'+s.total_cost_usd.toFixed(4))+
   card('Agents',Object.keys(s.by_agent).length);
 const rows=await j('/api/reviews');
 document.getElementById('empty').style.display=rows.length?'none':'block';
 const tb=document.querySelector('#queue tbody');tb.innerHTML='';
 for(const t of rows){
   const tr=document.createElement('tr');
   tr.innerHTML=`<td><code>${t.review_id.slice(0,28)}</code></td><td>${t.mode}</td>`+
     `<td><span class="pill ${t.status}">${t.status}</span></td><td>${t.n_findings}</td>`+
     `<td class="muted">${t.reason||''}</td><td></td>`;
   if(t.status==='pending'){
     const cell=tr.lastElementChild;
     cell.appendChild(btn('approve',t.review_id));cell.appendChild(btn('reject',t.review_id));
   }
   tb.appendChild(tr);
 }
}
function card(l,n){return `<div class="card"><div class="muted">${l}</div><div class="n">${n}</div></div>`}
function btn(kind,id){const b=document.createElement('button');b.textContent=kind;
 b.onclick=async()=>{await j('/api/hitl/'+id+'/decide',{method:'POST',headers:{'content-type':'application/json'},
   body:JSON.stringify({decision:kind,reviewer:'dashboard'})});refresh()};return b}
refresh();setInterval(refresh,4000);
</script></body></html>"""
