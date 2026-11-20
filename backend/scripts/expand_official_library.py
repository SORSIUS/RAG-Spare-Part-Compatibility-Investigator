"""Download and register a bounded, deduplicated official automotive reference set."""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from pypdf import PdfReader
from app.core.settings import Settings
from app.repositories.document_library import DocumentLibrary

REFERENCES = [
 ('denso_spark_plug_australia_2025.pdf','https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_2_australia_2025.pdf','Australia'),
 ('denso_spark_plug_tt_australia.pdf','https://www.denso.com.au/public/resources/DENSO_%20Spark%20Plug%20TT%20Catalogue.pdf','Australia'),
 ('denso_spark_plug_australia_2021.pdf','https://www.denso.com.au/public/resources/DENSO_SparkPlugCatalogue-2021_Australia.pdf','Australia'),
 ('denso_compressor_oil_manual.pdf','https://www.denso.com.au/public/resources/DENSO%20Service%20Manual_Compressor%20Oil%20Replenishment%20Quantities.pdf','Manufacturer component reference'),
 ('denso_magnetic_clutch_manual.pdf','https://www.denso.com.au/public/resources/DENSO%20Service%20Manual_Magnetic%20Clutch.pdf','Manufacturer component reference'),
 ('denso_dl_pulley_manual.pdf','https://www.denso.com.au/public/resources/DENSO%20Service%20Manual_DL%20Pulley_Complete.pdf','Manufacturer component reference'),
 ('denso_glow_plug_australia.pdf','https://www.denso.com.au/public/resources/DENSO_Glow%20Plug%20Catalogue.pdf','Australia'),
 ('denso_diesel_fuel_filters_australia_2020.pdf','https://www.denso.com.au/public/resources/DENSO_Diesel%20Fuel%20Filter%20CATALOGUE%202020_LoRes.pdf','Australia'),
 ('denso_product_overview_europe.pdf','https://assets.denso-am.eu/production/attachments/DENSO_Product_Brochure_EN.pdf','Europe'),
 ('ate_drum_brakes_2025.pdf','https://www.ate.de/media/5615/catalogue-ate-drum-brakes-trommelbremsen-2025_v3.pdf','Europe; application catalogue'),
 ('toyota_corolla_2012_owner_manual_north_america.pdf','https://www.toyota.ca/content/dam/toyota/documents/manuals/en/OM12F48U/OM12F48U.pdf','North America; not Pakistan fitment proof'),
 ('toyota_corolla_2012_quick_reference_usa.pdf','https://assets.sia.toyota.com/publications/en/om-s/OM12E1QRG/pdf/2012%20Corolla.pdf','USA; not Pakistan fitment proof'),
 ('toyota_corolla_2012_maintenance_usa.pdf','https://assets.sia.toyota.com/publications/en/omms-s/T-MMS-12Corolla/pdf/2012_Toyota_Corolla_WMG.pdf','USA; not Pakistan fitment proof'),
]

def main():
 settings=Settings(); folder=settings.backend_dir/'data/sources/official_expansion';folder.mkdir(parents=True,exist_ok=True)
 existing={hashlib.sha256(f.read_bytes()).hexdigest():f for f in (settings.backend_dir/'data/sources').rglob('*.pdf') if f.parent!=folder}
 def download(item):
  name,url,market=item; path=folder/name; partial=path.with_suffix('.download');entry={'name':name,'url':url,'market':market}
  try:
   if not path.exists():
    with httpx.stream('GET',url,follow_redirects=True,timeout=60) as response:
     response.raise_for_status(); size=0
     with partial.open('wb') as output:
      for chunk in response.iter_bytes():
       size+=len(chunk)
       if size>25*1024*1024: raise ValueError('Over the app upload limit (25 MB)')
       output.write(chunk)
    if not partial.read_bytes()[:8].startswith(b'%PDF'): raise ValueError('Not a PDF response')
    reader=PdfReader(partial)
    if reader.is_encrypted and not reader.decrypt(''): raise ValueError('Encrypted PDF')
    pages=len(reader.pages); partial.replace(path)
   else: pages=len(PdfReader(path).pages)
   sha=hashlib.sha256(path.read_bytes()).hexdigest()
   if sha in existing:
    path.unlink();path=existing[sha];status='already_present'
   else: status='downloaded'
   return {**entry,'status':status,'path':str(path.resolve()),'sha256':sha,'pages':pages,'bytes':path.stat().st_size}
  except Exception as error:
   return {**entry,'status':'failed','error':str(error).split('\n')[0][:250]}
  finally: partial.unlink(missing_ok=True)
 with ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(download,REFERENCES))
 library=DocumentLibrary(settings.runtime_dir)
 for entry in results:
  if entry['status']!='failed':
   record=library.register(Path(entry['path']),entry['name'],entry['sha256']);entry['library_status']=record['status']
  print(entry['status']+': '+entry['name']+((' — '+entry['error']) if entry['status']=='failed' else ''),flush=True)
 manifest=settings.backend_dir.parent/'docs/OFFICIAL_PDF_DOWNLOADS.json'
 manifest.write_text(json.dumps({'updated_at':datetime.now(timezone.utc).isoformat(),'scope':'Missing relevant car-reference PDFs from the official pages previously shared, plus Corolla 2012 manuals and a brake catalogue. Existing regional PDFs kept; combined duplicate bundles, non-car equipment and legal PDFs excluded.','documents':results},indent=2),encoding='utf-8')
 print('Downloads registered. Preparing searchable text locally (no LLM calls).',flush=True)
 library.run_pending()
 selected={e.get('sha256') for e in results}
 statuses=[{'name':r['name'],'status':r['status'],'error':r.get('error')} for r in library.list() if r['id'] in selected]
 print(json.dumps({'downloaded':sum(e['status']=='downloaded' for e in results),'already_present':sum(e['status']=='already_present' for e in results),'failed':sum(e['status']=='failed' for e in results),'library':statuses}),flush=True)

if __name__=='__main__': main()
