import os, gzip, base64, tempfile
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
import requests

pfx_path = r'C:\Users\Alexandre\Desktop\Certificado_A1_ASBF_02293109000190.pfx'
password = b'097764'

print("Lendo certificado PFX...")
with open(pfx_path, 'rb') as f:
    pfx_data = f.read()

private_key, cert, add_certs = pkcs12.load_key_and_certificates(pfx_data, password)
print("Certificado carregado:", cert.subject)

with tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as cert_file, \
     tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as key_file:
    
    cert_file.write(cert.public_bytes(Encoding.PEM))
    if add_certs:
        for ac in add_certs:
            cert_file.write(ac.public_bytes(Encoding.PEM))
    cert_path = cert_file.name

    key_file.write(private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption()
    ))
    key_path = key_file.name

print(f"Arquivos temporarios PEM criados: {cert_path}, {key_path}")

url = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}

ult_nsu = "000000000000000"
all_docs = []

try:
    xml_envio = """<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
  <tpAmb>1</tpAmb>
  <cUFAutor>41</cUFAutor>
  <CNPJ>02293109000190</CNPJ>
  <consNSU>
    <NSU>000000000000171</NSU>
  </consNSU>
</distDFeInt>"""

    soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <nfeDadosMsg>{xml_envio}</nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>"""

    resp = requests.post(url, data=soap_envelope.encode('utf-8'), headers=headers, cert=(cert_path, key_path), timeout=35)
    root = ET.fromstring(resp.text)
    
    cStat = ""
    xMotivo = ""
    for el in root.iter():
        tag = el.tag.split('}')[-1]
        if tag == 'cStat': cStat = el.text
        elif tag == 'xMotivo': xMotivo = el.text

    print(f"Resultado consNSU 171: cStat={cStat} ({xMotivo})")

    for doc_zip in root.iter():
        if doc_zip.tag.endswith('docZip'):
            nsu_doc = doc_zip.attrib.get('NSU', '')
            raw_b64 = doc_zip.text
            if raw_b64:
                try:
                    dec = gzip.decompress(base64.b64decode(raw_b64)).decode('utf-8', errors='ignore')
                    print("XML DO DOCUMENTO ENCONTRADO:\n", dec[:2000])
                except Exception as ed:
                    print("Erro dec:", ed)

except Exception as e:
    print("Erro na conexao com SEFAZ:", e)
finally:
    try:
        os.remove(cert_path)
        os.remove(key_path)
    except:
        pass
