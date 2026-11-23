/* Money Hunter AI assisted public-record search bot. Runs in-browser; query terms leave the device only when a search link is opened. */
(()=>{
"use strict";
const KEY="mh_ai_v2", RUNKEY="mh_bot_runs_v1";
const SOURCES=[
{name:"National unclaimed property",domain:"missingmoney.com",url:"https://www.missingmoney.com/",note:"NAUPA-sponsored multi-state search; search the full name manually."},
{name:"Official state programs",domain:"unclaimed.org",url:"https://unclaimed.org/search/",note:"Find each state's official program."},
{name:"Unpaid wages",domain:"webapps.dol.gov",url:"https://webapps.dol.gov/WOW/",note:"Department of Labor back-wage search."},
{name:"Missing pensions",domain:"pbgc.gov",url:"https://www.pbgc.gov/workers-retirees/find-unclaimed-retirement-benefits",note:"Pension benefits search."},
{name:"VA life insurance",domain:"va.gov",url:"https://insurance.va.gov/",note:"Only for eligible VA policyholders or beneficiaries."},
{name:"FHA mortgage refunds",domain:"hud.gov",url:"https://entp.hud.gov/dsrs/refunds/",note:"Potential FHA mortgage insurance refunds."},
{name:"IRS tax refunds",domain:"irs.gov",url:"https://www.irs.gov/wheres-my-refund",note:"Use IRS status tool for a filed return."},
{name:"SEC distributions",domain:"sec.gov",url:"https://www.sec.gov/enforce/investor-alerts-and-bulletins/investor-alert-unclaimed-funds",note:"Only eligible investors or claimants."},
{name:"FDIC failed-bank funds",domain:"fdic.gov",url:"https://closedbanks.fdic.gov/funds/",note:"Funds associated with failed insured banks."},
{name:"NCUA credit union funds",domain:"ncua.gov",url:"https://ncua.gov/support-services/conservatorships-liquidations",note:"Liquidated credit-union resources."},
{name:"Treasury savings bonds",domain:"treasurydirect.gov",url:"https://www.treasurydirect.gov/savings-bonds/",note:"Search eligible savings bonds."},
{name:"Bankruptcy court funds",domain:"uscourts.gov",url:"https://www.uscourts.gov/",note:"Court-specific funds; district and case details matter."},
{name:"Interior trust accounts",domain:"doi.gov",url:"https://www.doi.gov/ost/financial-management/individual-indian-money-iim",note:"Specialized trust accounts; only if applicable."},
{name:"Railroad Retirement",domain:"rrb.gov",url:"https://www.rrb.gov/Benefits/FinancialAssistance/UnclaimedFunds",note:"Only if you or an eligible beneficiary had benefits."}
];
const $=id=>document.getElementById(id), norm=s=>String(s||"").trim().replace(/\s+/g," ");
function load(){try{return JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){return {}}}
function esc(s){return String(s||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function getProfile(){const p=load().profile||{};return {name:norm(p.name),aliases:(p.aliases||[]).map(norm).filter(Boolean),places:(p.places||[]).map(norm).filter(Boolean),state:norm(p.homeState)}}
function makeTasks(){
 const p=getProfile(),names=[p.name,...p.aliases].filter(Boolean),places=[...p.places,p.state].filter(Boolean),tasks=[];
 if(!names.length)return tasks;
 SOURCES.forEach(src=>names.forEach(name=>{
  const loc=places.length?' ("'+places.slice(0,2).join('" OR "')+'")':"";
  const q='site:'+src.domain+' "'+name+'"'+loc;
  tasks.push({source:src.name,name:name,domain:src.domain,url:src.url,note:src.note,q:q,search:"https://www.google.com/search?q="+encodeURIComponent(q)});
 }));
 names.forEach(name=>{
  const q='"'+name+'" ("unclaimed property" OR "unclaimed funds" OR "missing money") United States';
  tasks.push({source:"Broader public web search",name:name,domain:"web",url:"https://unclaimed.org/search/",note:"Searches indexed public pages only; verify at the official agency.",q:q,search:"https://www.google.com/search?q="+encodeURIComponent(q)});
 });
 return tasks;
}
function history(){try{return JSON.parse(localStorage.getItem(RUNKEY)||"[]")}catch(e){return []}}
function saveHistory(a){localStorage.setItem(RUNKEY,JSON.stringify(a.slice(0,30)))}
function render(){
 const p=getProfile(),tasks=makeTasks();
 $("botProfileStatus").textContent=p.name?"Using saved profile: "+p.name+" · "+p.aliases.length+" former name(s)":"Save your name in My profile first.";
 $("botCount").textContent=tasks.length+" prepared searches";
 $("botTasks").innerHTML=tasks.length?tasks.map((t,i)=>'<article class="match"><div class="row"><div><b>'+esc(t.source)+'</b><div class="tiny muted">'+esc(t.name)+' · '+esc(t.domain)+'</div></div><a class="btn secondary fit" href="'+esc(t.search)+'" target="_blank" rel="noopener">Search public web ↗</a></div><p class="tiny muted">'+esc(t.note)+'</p><div class="tiny">'+esc(t.q)+'</div><a class="tiny" href="'+esc(t.url)+'" target="_blank" rel="noopener">Open official database ↗</a></article>').join(""):'<p class="muted">Add your full name in My profile to prepare searches.</p>';
 $("botHistory").innerHTML=history().map(h=>'<div class="source"><div class="desc"><b>'+esc(h.name)+'</b><div class="tiny muted">'+esc(h.date)+' · '+esc(h.count)+' search links prepared</div></div><span class="tag">Prepared</span></div>').join("")||'<p class="muted tiny">No search sessions recorded yet.</p>';
}
function start(){
 const p=getProfile(),tasks=makeTasks();
 if(!p.name){alert("Save your full name in My profile first.");return}
 if(!$("botConsent").checked){alert("Confirm that your name and selected city/state terms will be sent to Google when you open a search.");return}
 const h=history();h.unshift({name:p.name,date:new Date().toLocaleString(),count:tasks.length});saveHistory(h);render();
 $("botNotice").textContent="Search plan prepared. Open each public-web search, then verify any lead directly with the official agency. No government record is confirmed by this step.";
}
document.addEventListener("DOMContentLoaded",()=>{
 if(!$("botTasks"))return;
 $("runBot").addEventListener("click",start);$("refreshBot").addEventListener("click",render);
 $("openOfficial").addEventListener("click",()=>{if(!getProfile().name){alert("Save your full name in My profile first.");return}window.open("https://www.missingmoney.com/","_blank","noopener");window.open("https://unclaimed.org/search/","_blank","noopener")});
 render();
});
})();
