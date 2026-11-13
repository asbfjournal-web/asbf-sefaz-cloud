import os, gzip, base64, tempfile, time, json
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
import requests

pfx_path = r"C:\Users\Alexandre\Desktop\Certificado_A1_ASBF_02293109000190.pfx"
password = b"097764"

with open(pfx_path, "rb") as f:
    pfx_data = f.read()

private_key, cert, add_certs = pkcs12.load_key_and_certificates(pfx_data, password)

cert_file = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
key_file = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
cert_file.write(cert.public_bytes(Encoding.PEM))
if add_certs:
    for ac in add_certs:
        cert_file.write(ac.public_bytes(Encoding.PEM))
cert_path = cert_file.name
cert_file.close()

key_file.write(private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
key_path = key_file.name
key_file.close()

url = https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx
headers = {Content-Type: application/soap+xml; charset=utf-8}
ult_nsu = 000000000000000
all_docs = []

for attempt in range(25):
    xml_envio = <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01"><tpAmb>1</tpAmb><cUFAutor>41</cUFAutor><CNPJ>02293109000190</CNPJ><distNSU><ultNSU> + ult_nsu + </ultNSU></distNSU></distDFeInt>
    soap = <?xml version="1.0" encoding="utf-8"?><soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"><soap12:Body><nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe"><nfeDadosMsg> + xml_envio + </nfeDadosMsg></nfeDistDFeInteresse></soap12:Body></soap12:Envelope>
    
    try:
        resp = requests.post(url, data=soap.encode(utf-8), headers=headers, cert=(cert_path, key_path), timeout=35)
        root = ET.fromstring(resp.text)
    except Exception as e:
        print(Erro requisicao:, e)
        break
    
    cStat = "
 xMotivo = 
 new_ult_nsu = ult_nsu
 maxNSU = 
 
 for elem in root.iter():
 tag = elem.tag.split(})[-1]
 if tag == cStat: cStat = elem.text
 elif tag == xMotivo: xMotivo = elem.text
 elif tag == ultNSU: new_ult_nsu = elem.text
 elif tag == maxNSU: maxNSU = elem.text
 
 print(fConsulta {attempt+1}: ultNSU={ult_nsu} -> cStat={cStat} ({xMotivo}), nextNSU={new_ult_nsu}, maxNSU={maxNSU})
 
 for doc_zip in root.iter():
 if doc_zip.tag.endswith(docZip):
 nsu_doc = doc_zip.attrib.get(NSU, )
 raw_b64 = doc_zip.text
 if raw_b64:
 try:
 dec = gzip.decompress(base64.b64decode(raw_b64)).decode(utf-8, errors=ignore)
 droot = ET.fromstring(dec)
 doc_type = droot.tag.split(})[-1]
 info = {NSU: nsu_doc, type: doc_type}
 for el in droot.iter():
 t = el.tag.split(})[-1]
 if t in [chNFe, CNPJ, xNome, vNF, dhEmi, nProt, cSitNFe, xJust]:
 info[t] = el.text
 print(   >>> DOCUMENTO FISCAL:, info)
 all_docs.append(info)
 except Exception as ex:
 print(   Erro descompressao:, ex)
 
 if new_ult_nsu == ult_nsu or cStat == 137:
 print(Nao ha mais novos documentos no SEFAZ.)
 break
 ult_nsu = new_ult_nsu
 time.sleep(1.5)

try:
 os.remove(cert_path)
 os.remove(key_path)
except: pass

print(f\nTOTAL DE DOCUMENTOS ENCONTRADOS NA SEFAZ: {len(all_docs)})
with open(sefaz_resgatados.json, w, encoding=utf-8) as out:
 json.dump(all_docs, out, ensure_ascii=False, indent=2)
