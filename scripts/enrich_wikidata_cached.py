#!/usr/bin/env python3
"""Enrich the corporate people whose exact Wikipedia titles are already cached."""
import csv, json, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from euro_sdt.v2.db import V2_DB_PATH, connect, now, uid
WIKI="https://en.wikipedia.org/w/api.php"; WD="https://www.wikidata.org/w/api.php"
UA="euro-sdt/0.3 (research)"; CACHE=Path("data/corporate/wikidata_cache.json"); OUT=Path("data/corporate/wikidata_matches.csv")
def norm(v):
 v=unicodedata.normalize("NFKD",v or "").encode("ascii","ignore").decode(); v=re.sub(r"^(dr|prof|sir|dame|lord|ladyship)\.?\s+","",v,flags=re.I); return re.sub(r"[^a-z0-9]+","",v.lower())
def get(u):
 req=urllib.request.Request(u,headers={"User-Agent":UA})
 with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
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
 cache=json.loads(CACHE.read_text()) if CACHE.exists() else {}
 titles={v["title"]:k for k,v in cache.items() if v.get("title")}
 qids={}
 items=list(titles)
 for i in range(0,len(items),50):
  u=WIKI+"?"+urllib.parse.urlencode({"action":"query","prop":"pageprops","titles":"|".join(items[i:i+50]),"redirects":1,"format":"json"})
  d=get(u)
  for p in d.get("query",{}).get("pages",{}).values():
   if p.get("pageprops",{}).get("wikibase_item"): qids[norm(p["title"])]=p["pageprops"]["wikibase_item"]
  time.sleep(3)
 ents={}
 qid_list=list(set(qids.values()))
 for i in range(0,len(qid_list),50):
  u=WD+"?"+urllib.parse.urlencode({"action":"wbgetentities","ids":"|".join(qid_list[i:i+50]),"props":"claims|labels|descriptions","languages":"en","format":"json"})
  ents.update(get(u).get("entities",{})); time.sleep(0.5)
 vals=set()
 for d in ents.values():
  for p in ("P27","P69","P106","P108","P39","P1416"): vals.update(cids(d,p))
 labels={}
 for i in range(0,len(vals),50):
  u=WD+"?"+urllib.parse.urlencode({"action":"wbgetentities","ids":"|".join(sorted(vals)[i:i+50]),"props":"labels","languages":"en","format":"json"})
  for q,e in get(u).get("entities",{}).items(): labels[q]=(e.get("labels",{}).get("en",{}) or {}).get("value",q)
  time.sleep(0.5)
 rows=[("person","qid","label","description","confidence")]; profiles=0
 for pid,entry in cache.items():
  title=entry.get("title")
  if not title: continue
  qid=qids.get(norm(title))
  if not qid or qid not in ents: continue
  d=ents[qid]; desc=(d.get("descriptions",{}).get("en",{}) or {}).get("value",""); name=(d.get("labels",{}).get("en",{}) or {}).get("value",title)
  rows.append((entry.get("name",title),qid,name,desc,"exact_title"))
  r=db.execute("select external_ids_json from entity where id=?",(pid,)).fetchone(); ext=json.loads(r[0]) if r and r[0] else {}; ext["wikidata"]=qid
  db.execute("update entity set external_ids_json=? where id=?",(json.dumps(ext,ensure_ascii=False),pid))
  attrs=[("description",desc,None),("birth_date",birth(d),None)]
  for p,a in (("P27","citizenship"),("P69","education"),("P106","occupation"),("P108","employer"),("P39","position"),("P1416","member_of")):
   for v in cids(d,p): attrs.append((a,labels.get(v,v),v))
  for a,v,vid in attrs:
   if not v: continue
   db.execute("insert or replace into person_profile (id,entity_id,attribute,value,value_id,quote,status,source_url,notes,created_at) values (?,?,?,?,?,?,?,?,?,?)",(uid("pp-"),pid,a,v,vid,f"Wikidata {qid} {a}","wikidata",f"https://www.wikidata.org/wiki/{qid}","Wikidata structured fact; QID is the provenance key",now())); profiles+=1
 db.commit(); Path(OUT).write_text("\n".join(",".join(x) for x in rows),encoding="utf-8"); print("matched",len(rows)-1,"profiles",profiles)
if __name__=="__main__": main()
