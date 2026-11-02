#!/usr/bin/env python3
"""Enrich all corporate people via exact Wikipedia title -> Wikidata."""
from __future__ import annotations
import csv, json, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from euro_sdt.v2.db import V2_DB_PATH, connect, now, uid
WIKI="https://en.wikipedia.org/w/api.php"; WD="https://www.wikidata.org/w/api.php"
OUT=Path("data/corporate/wikidata_matches.csv"); UA="euro-sdt/0.3 (research)"
def norm(v):
 v=unicodedata.normalize("NFKD",v or "").encode("ascii","ignore").decode(); v=re.sub(r"^(dr|prof|sir|dame|lord|ladyship)\.?\s+","",v,flags=re.I); return re.sub(r"[^a-z0-9]+","",v.lower())
def get(u):
 req=urllib.request.Request(u,headers={"User-Agent":UA})
 for i in range(5):
  try:
   with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
  except Exception:
   if i==4: raise
   time.sleep(3*(i+1))
def cids(d,p):
 out=[]
 for c in d.get("claims",{}).get(p,[]):
  v=c.get("mainsnak",{}).get("datavalue",{}).get("value")
  if isinstance(v,dict) and v.get("id"): out.append(v["id"])
 return list(dict.fromkeys(out))
def birth(d):
 cs=d.get("claims",{}).get("P569",[])
 if not cs: return None
 v=cs[0].get("mainsnak",{}).get("datavalue",{}).get("value")
 if not isinstance(v,dict): return None
 m=re.match(r"[+-](\d{4})-(\d{2})-(\d{2})",v.get("time",""))
 if not m: return None
 y,mo,da=m.groups(); return y if mo=="00" else (f"{y}-{mo}" if da=="00" else f"{y}-{mo}-{da}")
def main():
 db=connect(V2_DB_PATH); db.row_factory=__import__("sqlite3").Row
 people=db.execute("select distinct e.id,e.name from entity e join role_tenure t on t.person_id=e.id where t.tenure_type='corporate_role' order by e.name").fetchall()
 qid_by_norm={}
 for i in range(0,len(people),50):
  names=[p["name"] for p in people[i:i+50]]
  u=WIKI+"?"+urllib.parse.urlencode({"action":"query","prop":"pageprops","titles":"|".join(names),"redirects":1,"format":"json"})
  d=get(u)
  for page in d.get("query",{}).get("pages",{}).values():
   q=page.get("pageprops",{}).get("wikibase_item")
   if q: qid_by_norm[norm(page.get("title",""))]=q
  time.sleep(2)
 pairs=[]
 for p in people:
  q=qid_by_norm.get(norm(p["name"]))
  if q: pairs.append((p,q))
 ents={}; qlist=sorted({q for _,q in pairs})
 for i in range(0,len(qlist),50):
  u=WD+"?"+urllib.parse.urlencode({"action":"wbgetentities","ids":"|".join(qlist[i:i+50]),"props":"claims|labels|descriptions","languages":"en","format":"json"})
  ents.update(get(u).get("entities",{})); time.sleep(0.5)
 vals=set()
 for d in ents.values():
  for p in ("P27","P69","P106","P108","P39","P1416"): vals.update(cids(d,p))
 labels={}; vals=sorted(vals)
 for i in range(0,len(vals),50):
  u=WD+"?"+urllib.parse.urlencode({"action":"wbgetentities","ids":"|".join(vals[i:i+50]),"props":"labels","languages":"en","format":"json"})
  for q,e in get(u).get("entities",{}).items(): labels[q]=(e.get("labels",{}).get("en",{}) or {}).get("value",q)
  time.sleep(0.5)
 out=[("person","qid","label","description","birth_date")]; profiles=0
 for p,qid in pairs:
  d=ents.get(qid,{}); b=birth(d)
  if b and int(b[:4]) < 1940: continue
  desc=(d.get("descriptions",{}).get("en",{}) or {}).get("value",""); label=(d.get("labels",{}).get("en",{}) or {}).get("value","")
  out.append((p["name"],qid,label,desc,b or ""))
  r=db.execute("select external_ids_json from entity where id=?",(p["id"],)).fetchone(); ext=json.loads(r[0]) if r and r[0] else {}; ext["wikidata"]=qid
  db.execute("update entity set external_ids_json=? where id=?",(json.dumps(ext,ensure_ascii=False),p["id"]))
  attrs=[("description",desc,None),("birth_date",b,None)]
  for prop,attr in (("P27","citizenship"),("P69","education"),("P106","occupation"),("P108","employer"),("P39","position"),("P1416","member_of")):
   for v in cids(d,prop): attrs.append((attr,labels.get(v,v),v))
  for a,v,vid in attrs:
   if not v: continue
   db.execute("insert into person_profile (id,entity_id,attribute,value,value_id,quote,status,source_url,notes,created_at) values (?,?,?,?,?,?,?,?,?,?)",(uid("pp-"),p["id"],a,v,vid,f"Wikidata {qid} {a}","wikidata_title_match",f"https://www.wikidata.org/wiki/{qid}","Exact Wikipedia title match; QID should be checked before analysis",now())); profiles+=1
 db.commit()
 with OUT.open("w",newline="",encoding="utf-8") as f: csv.writer(f).writerows(out)
 print("people",len(people),"matched",len(pairs),"profiles",profiles)
if __name__=="__main__": main()
