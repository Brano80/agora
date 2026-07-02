#!/usr/bin/env python3
"""Publish the manifesto to Zenodo and print the DOI.
Setup: pip install requests ; create a token at
  zenodo.org/account/settings/applications/tokens/new  (scopes: deposit:write, deposit:actions)
  export ZENODO_TOKEN=...           # use SANDBOX first: ZENODO_SANDBOX=1
Usage: python scripts/launch_zenodo.py [AGORA_Manifesto.pdf]
To publish a CORRECTED VERSION of an existing record (same concept DOI):
  ZENODO_NEW_VERSION=<record_id> python scripts/launch_zenodo.py corrected.pdf
NOTE: publishing mints a permanent DOI and cannot be deleted — test on sandbox first."""
import os, sys, json, requests
tok=os.environ.get("ZENODO_TOKEN") or sys.exit("Set ZENODO_TOKEN")
base="https://sandbox.zenodo.org/api" if os.environ.get("ZENODO_SANDBOX") else "https://zenodo.org/api"
pdf=sys.argv[1] if len(sys.argv)>1 else "AGORA_Manifesto.pdf"
h={"Authorization":f"Bearer {tok}"}
prev=os.environ.get("ZENODO_NEW_VERSION")
if prev:
    r=requests.post(f"{base}/deposit/depositions/{prev}/actions/newversion",headers=h); r.raise_for_status()
    d=requests.get(r.json()["links"]["latest_draft"],headers=h); d.raise_for_status(); d=d.json()
    for f0 in requests.get(d["links"]["files"],headers=h).json():   # drop inherited file
        requests.delete(f0["links"]["self"],headers=h)
else:
    d=requests.post(f"{base}/deposit/depositions",json={},headers=h); d.raise_for_status(); d=d.json()
with open(pdf,"rb") as f: requests.put(f"{d['links']['bucket']}/{os.path.basename(pdf)}",data=f,headers=h).raise_for_status()
meta={"metadata":{
 "title":"Owning the Machine: A Governance of Abundance for Europe",
 "upload_type":"publication","publication_type":"workingpaper",
 "description":("AGORA is an open, stock-flow-consistent model of the European economy that quantifies "
   "AI's distributional and fiscal impact and compares policy responses (cash UBI vs Universal Basic "
   "Capital) under transparent, swappable assumptions. Calibrated to live data for 26 EU member states "
   "and back-tested to ~2.3% mean GDP error (debt path within the 10% bound); a consistency gate enforces accounting integrity on every run. "
   "Sandbox, not oracle: scenario comparisons, not forecasts."),
 "creators":[{"name":"Ambroz, Branislav"}],
 "keywords":["artificial intelligence","labour share","income inequality","wealth distribution",
   "Universal Basic Capital","sovereign wealth fund","predistribution","stock-flow consistent model",
   "European Union","fiscal policy","AI windfall"],
 "license":"cc-by-4.0","access_right":"open"}}
requests.put(f"{base}/deposit/depositions/{d['id']}",data=json.dumps(meta),
  headers={**h,"Content-Type":"application/json"}).raise_for_status()
if input("Publishing mints a PERMANENT DOI. Type PUBLISH to proceed: ").strip() != "PUBLISH":
    sys.exit("aborted — nothing published (draft deposition left in your Zenodo uploads)")
p=requests.post(f"{base}/deposit/depositions/{d['id']}/actions/publish",headers=h); p.raise_for_status(); p=p.json()
print("DOI:",p["doi"]); print("Record:",p["links"]["record_html"])
