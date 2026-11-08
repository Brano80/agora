#!/usr/bin/env python3
"""Publish the manifesto to Zenodo and print the DOI.
Setup: pip install requests ; create a token at
  zenodo.org/account/settings/applications/tokens/new  (scopes: deposit:write, deposit:actions)
  export ZENODO_TOKEN=...           # use SANDBOX first: ZENODO_SANDBOX=1
Usage: python scripts/launch_zenodo.py [AGORA_Manifesto.pdf]
To publish a CORRECTED VERSION of an existing record (same concept DOI):
  ZENODO_NEW_VERSION=<record_id> python scripts/launch_zenodo.py corrected.pdf
  (v1.2: ZENODO_NEW_VERSION=21127193, the v1.1 record)
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
 "title":"Who Owns the Machine? AI, the Labour Share and Europe's Policy Choices",
 "version":"1.2",
 "upload_type":"publication","publication_type":"workingpaper",
 "description":("AGORA is an open, stock-flow-consistent model of 24 EU economies. It asks what happens "
   "to households and public finances if AI moves income from work to capital, and what cash transfers "
   "and citizen ownership (Universal Basic Capital) can and cannot do about it, under transparent, "
   "swappable assumptions; a consistency gate enforces accounting integrity on every run. Under the "
   "stated scenario (the labour share falling from 66% to 30% by 2048): the welfare state's wage-tax base "
   "erodes and public debt rises in every member state; cash UBI gives more consumption and Universal "
   "Basic Capital lower inequality and broader ownership, in every Monte-Carlo draw, and neither dominates; "
   "most of the AI rent is paid abroad, beyond the reach of domestic taxes. Over 2011-2019 the model "
   "tracks history no better than naive benchmarks: read the direction of the results, not the decimals. "
   "<br><br><b>Version 1.2 corrects versions 1.0 and 1.1</b> (titled 'Owning the Machine'). Their headline "
   "claims did not survive a rebuild of the model: the citizens' dividend overtaking cash, Universal Basic "
   "Capital dominating cash and inaction, reinvestment making the ownership economy larger, pooling halving "
   "the European gap, and validation against history (~2.3% GDP error). Each claim and its status: "
   "docs/FINDINGS-LEDGER.md at https://github.com/Brano80/agora. "
   "Sandbox, not oracle: scenario comparisons, not forecasts."),
 "creators":[{"name":"Ambroz, Branislav"}],
 "keywords":["artificial intelligence","labour share","income inequality","wealth distribution",
   "Universal Basic Capital","universal basic income","fiscal policy","stock-flow consistent model",
   "European Union","foreign ownership","model validation"],
 "related_identifiers":[{"identifier":"https://github.com/Brano80/agora","relation":"isSupplementedBy"}],
 "license":"cc-by-4.0","access_right":"open"}}
requests.put(f"{base}/deposit/depositions/{d['id']}",data=json.dumps(meta),
  headers={**h,"Content-Type":"application/json"}).raise_for_status()
if input("Publishing mints a PERMANENT DOI. Type PUBLISH to proceed: ").strip() != "PUBLISH":
    sys.exit("aborted — nothing published (draft deposition left in your Zenodo uploads)")
p=requests.post(f"{base}/deposit/depositions/{d['id']}/actions/publish",headers=h); p.raise_for_status(); p=p.json()
print("DOI:",p["doi"]); print("Record:",p["links"]["record_html"])
