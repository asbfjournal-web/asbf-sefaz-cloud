import os, tempfile, requests, lxml.etree as ET
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from signxml import XMLSigner, methods

PFX_PATH = 'Certificado_A1_ASBF_02293109000190.pfx'
CERT_PASSWORD = b'097764'
XML_PATH = r'C:\Users\Alexandre\Downloads\NFe-000002.xml'

with open(PFX_PATH, 'rb') as f:
    private_key, cert, add_certs = pkcs12.load_key_and_certificates(f.read(), CERT_PASSWORD)

cert_pem = cert.public_bytes(Encoding.PEM)
key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

parser = ET.XMLParser(remove_blank_text=True)
root = ET.parse(XML_PATH, parser).getroot()
nfe_node = root.find('{http://www.portalfiscal.inf.br/nfe}NFe') or root
inf_nfe = nfe_node.find('{http://www.portalfiscal.inf.br/nfe}infNFe')
ref_uri = inf_nfe.attrib['Id']

signer = XMLSigner(method=methods.enveloped, signature_algorithm='rsa-sha1', digest_algorithm='sha1', c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
signed_nfe = signer.sign(nfe_node, key=key_pem, cert=cert_pem, reference_uri=f'#{ref_uri}')
nfe_xml_str = ET.tostring(signed_nfe, encoding='utf-8').decode('utf-8')

soap = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">
      <enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
        <idLote>1</idLote>
        <indSinc>1</indSinc>
        {nfe_xml_str}
      </enviNFe>
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''

with tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as cf, tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as kf:
    cf.write(cert_pem)
    kf.write(key_pem)
    c_path, k_path = cf.name, kf.name

url = 'https://nfe.sefaz.pr.gov.br/nfe/NFeAutorizacao4'
resp = requests.post(url, data=soap.encode('utf-8'), headers={'Content-Type': 'application/soap+xml; charset=utf-8'}, cert=(c_path, k_path), timeout=30)
print('Status HTTP:', resp.status_code)
print('Retorno SEFAZ-PR:', resp.text)
