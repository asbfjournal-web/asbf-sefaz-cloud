# Suporte a Certificado via Base64 na Nuvem (Render/Cloud)
import base64
PFX_BASE64 = os.environ.get('PFX_BASE64', '')
if PFX_BASE64:
    with open(PFX_PATH, 'wb') as pf:
        pf.write(base64.b64decode(PFX_BASE64))

import os
import sys
import json
import gzip
import base64
import tempfile
import time
import threading
from datetime import datetime
import xml.etree.ElementTree as ET
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
import requests

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'nfe_database.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
PFX_PATH = os.environ.get('PFX_PATH', os.path.join(BASE_DIR, 'Certificado_A1_ASBF_02293109000190.pfx'))
CERT_PASSWORD = os.environ.get('CERT_PASSWORD', '097764').encode('utf-8')

# Dados iniciais autÃªnticos da ASBF
INITIAL_DATA = {
    "empresa": {
        "cnpj": "02293109000190",
        "razaoSocial": "ASBF REVISTAS TECNICAS INTERNACIONAIS LTDA",
        "uf": "PR"
    },
    "ultNSU": "000000000000170",
    "maxNSU": "000000000000170",
    "ultimoSync": "2026-10-02T12:30:00",
    "notas": [
        {
            "id": "rec-sefaz-35260903796758000257550020000992481256295013",
            "chave": "35260903796758000257550020000992481256295013",
            "numero": "99248",
            "serie": "2",
            "emitente": "EDITORA MELHORAMENTOS LTDA",
            "cnpjEmitente": "03.796.758/0002-57",
            "ufEmitente": "SP",
            "emissao": "28/09/2026",
            "dhAutorizacao": "28/09/2026 15:16:00",
            "valor": 1632.65,
            "valorProdutos": 1632.65,
            "tipoOperacao": "Compra de Livros para Revenda / Fornecedor",
            "situacaoSefaz": "Autorizada (DF-e SEFAZ Nacional)",
            "manifestacao": "CiÃªncia da EmissÃ£o",
            "statusFinanceiro": "Pendente de Pagamento",
            "nsu": "000000000000170",
            "origem": "SEFAZ Nacional DF-e (Certificado A1 ASBF)",
            "itens": [
                {
                    "codigo": "MELH-LIV-02",
                    "nome": "LIVROS DIDÃTICOS E LITERÃRIOS â€” EDITORA MELHORAMENTOS (PEDIDO 28/09)",
                    "ncm": "4901.99.00",
                    "cfop": "5102",
                    "un": "UN",
                    "qtd": 1,
                    "valorUnit": 1632.65,
                    "subtotal": 1632.65
                }
            ]
        },
        {
            "id": "rec-melhoramentos-99099-21set",
            "chave": "35260903796758000257550020000990991590873605",
            "numero": "99099",
            "serie": "2",
            "emitente": "EDITORA MELHORAMENTOS LTDA",
            "cnpjEmitente": "03.796.758/0002-57",
            "ufEmitente": "SP",
            "emissao": "21/09/2026",
            "dhAutorizacao": "21/09/2026 14:30:00",
            "valor": 470.35,
            "valorProdutos": 470.35,
            "tipoOperacao": "Compra de Livros para Revenda / Fornecedor",
            "situacaoSefaz": "Autorizada (SEFAZ/SP)",
            "manifestacao": "CiÃªncia da EmissÃ£o",
            "statusFinanceiro": "LanÃ§ado no Contas a Pagar",
            "origem": "Compra de Livros ASBF (21/09/2026)",
            "itens": [
                {
                    "codigo": "MELH-LIV-01",
                    "nome": "LIVROS DIDÃTICOS E LITERÃRIOS â€” EDITORA MELHORAMENTOS (PEDIDO 21/09)",
                    "ncm": "4901.99.00",
                    "cfop": "5102",
                    "un": "UN",
                    "qtd": 1,
                    "valorUnit": 470.35,
                    "subtotal": 470.35
                }
            ]
        }
    ]
}

def load_db():
    if not os.path.exists(DB_FILE):
        save_db(INITIAL_DATA)
        return INITIAL_DATA
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return INITIAL_DATA

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def consultar_sefaz_dfe():
    if not os.path.exists(PFX_PATH):
        return {"status": "erro", "motivo": f"Arquivo PFX nÃ£o encontrado em {PFX_PATH}"}
    
    db = load_db()
    ult_nsu = db.get("ultNSU", "000000000000000")
    
    with open(PFX_PATH, 'rb') as f:
        pfx_data = f.read()

    try:
        private_key, cert, add_certs = pkcs12.load_key_and_certificates(pfx_data, CERT_PASSWORD)
    except Exception as e:
        return {"status": "erro", "motivo": f"Erro de senha do certificado: {str(e)}"}

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

    xml_envio = f"""<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
  <tpAmb>1</tpAmb>
  <cUFAutor>41</cUFAutor>
  <CNPJ>02293109000190</CNPJ>
  <distNSU>
    <ultNSU>{ult_nsu}</ultNSU>
  </distNSU>
</distDFeInt>"""

    soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <nfeDadosMsg>{xml_envio}</nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>"""

    url = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
    headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}

    novas_notas = 0
    cStat = "0"
    xMotivo = ""

    try:
        resp = requests.post(url, data=soap_envelope.encode('utf-8'), headers=headers, cert=(cert_path, key_path), timeout=35)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            ns = {'soap': 'http://www.w3.org/2003/05/soap-envelope', 'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            cStat_elem = root.find('.//nfe:cStat', ns)
            if cStat_elem is None:
                # Tentar sem namespace
                for elem in root.iter():
                    if elem.tag.endswith('cStat'):
                        cStat = elem.text
                    elif elem.tag.endswith('xMotivo'):
                        xMotivo = elem.text
                    elif elem.tag.endswith('ultNSU'):
                        db['ultNSU'] = elem.text
                    elif elem.tag.endswith('maxNSU'):
                        db['maxNSU'] = elem.text
            else:
                cStat = cStat_elem.text
                xMotivo_elem = root.find('.//nfe:xMotivo', ns)
                if xMotivo_elem is not None:
                    xMotivo = xMotivo_elem.text
            
            # Percorrer docs retornados
            for doc_zip in root.iter():
                if doc_zip.tag.endswith('docZip'):
                    nsu_doc = doc_zip.attrib.get('NSU', '')
                    raw_b64 = doc_zip.text
                    if raw_b64:
                        try:
                            decompressed = gzip.decompress(base64.b64decode(raw_b64)).decode('utf-8', errors='ignore')
                            doc_root = ET.fromstring(decompressed)
                            
                            # resNFe
                            if 'resNFe' in doc_root.tag:
                                chave = doc_root.find('.//{*}chNFe')
                                emit_cnpj = doc_root.find('.//{*}CNPJ')
                                emit_nome = doc_root.find('.//{*}xNome')
                                v_nf = doc_root.find('.//{*}vNF')
                                dh_emi = doc_root.find('.//{*}dhEmi')
                                
                                chave_val = chave.text if chave is not None else ''
                                if chave_val:
                                    # Verificar se ja existe
                                    if not any(x['chave'] == chave_val for x in db['notas']):
                                        db['notas'].insert(0, {
                                            "id": f"rec-sefaz-{chave_val}",
                                            "chave": chave_val,
                                            "numero": chave_val[25:34].lstrip('0') or '0',
                                            "serie": str(int(chave_val[22:25])),
                                            "emitente": emit_nome.text if emit_nome is not None else 'FORNECEDOR',
                                            "cnpjEmitente": emit_cnpj.text if emit_cnpj is not None else '',
                                            "ufEmitente": "SP",
                                            "emissao": dh_emi.text[:10] if dh_emi is not None else datetime.now().strftime('%Y-%m-%d'),
                                            "valor": float(v_nf.text) if v_nf is not None else 0.0,
                                            "valorProdutos": float(v_nf.text) if v_nf is not None else 0.0,
                                            "tipoOperacao": "Compra de Livros / Fornecedor",
                                            "situacaoSefaz": "Autorizada (SEFAZ DF-e)",
                                            "manifestacao": "CiÃªncia da EmissÃ£o",
                                            "statusFinanceiro": "Pendente de Pagamento",
                                            "nsu": nsu_doc,
                                            "origem": "SEFAZ Nacional DF-e AutomÃ¡tico",
                                            "itens": []
                                        })
                                        novas_notas += 1
                        except Exception as e_dec:
                            pass
            
            db['ultimoSync'] = datetime.now().isoformat()
            save_db(db)
            return {"status": "ok", "cStat": cStat, "xMotivo": xMotivo, "novasNotas": novas_notas, "totalNotas": len(db['notas']), "ultNSU": db.get("ultNSU")}
        else:
            return {"status": "erro", "httpCode": resp.status_code, "resposta": resp.text[:200]}
    except Exception as e:
        return {"status": "erro", "motivo": str(e)}
    finally:
        try:
            os.remove(cert_path)
            os.remove(key_path)
        except:
            pass

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "online",
        "servico": "ASBF SEFAZ Cloud Sync",
        "empresa": "ASBF REVISTAS TÃ‰CNICAS INTERNACIONAIS LTDA",
        "cnpj": "02.293.109/0001-90",
        "certificadoValidoAte": "2027-09-09",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/nfe/recebidas', methods=['GET'])
def get_recebidas():
    db = load_db()
    return jsonify({
        "status": "ok",
        "total": len(db.get("notas", [])),
        "ultimoSync": db.get("ultimoSync"),
        "ultNSU": db.get("ultNSU"),
        "notas": db.get("notas", [])
    })

@app.route('/api/nfe/sincronizar', methods=['POST', 'GET'])
def trigger_sync():
    res = consultar_sefaz_dfe()
    return jsonify(res)


# === ROTA DE EMISSÃO NF-E 4.00 SEFAZ-PR ===
import random
from xml.sax.saxutils import escape
import lxml.etree as LET
from signxml import XMLSigner, methods

def calcular_dv_chave(chave43):
    pesos = [2,3,4,5,6,7,8,9]
    soma = sum(int(d) * pesos[i % 8] for i, d in enumerate(reversed(chave43)))
    resto = soma % 11
    return '0' if resto in (0, 1) else str(11 - resto)

def montar_xml_nfe_400(n):
    cUF = '41'
    emissao_str = str(n.get('emissao') or datetime.now().strftime('%Y-%m-%d'))[:10]
    aamm = emissao_str[2:4] + emissao_str[5:7]
    cnpj_emit = '02293109000190'
    mod = '55'
    serie = str(int(n.get('serie') or 2)).zfill(3)
    nNF_int = int(n.get('numero') or 2)
    nNF = str(nNF_int).zfill(9)
    tpEmis = '1'
    cNF = str(nNF_int + 10000000)[-8:]
    chave43 = f"{cUF}{aamm}{cnpj_emit}{mod}{serie}{nNF}{tpEmis}{cNF}"
    cDV = calcular_dv_chave(chave43)
    chave = chave43 + cDV

    cnpj_dest = ''.join(filter(str.isdigit, str(n.get('cnpj') or '')))
    dest_uf = 'PR'
    cid_uf = str(n.get('destCidadeUf') or 'Astorga/PR')
    if '/' in cid_uf:
        partes = cid_uf.split('/')
        dest_xMun, dest_uf = partes[0].strip(), partes[1].strip().upper()[:2]
    elif '-' in cid_uf:
        partes = cid_uf.split('-')
        dest_xMun, dest_uf = partes[0].strip(), partes[1].strip().upper()[:2]
    else:
        dest_xMun = cid_uf.strip() or 'Astorga'

    idDest = '1' if dest_uf == 'PR' else '2'
    cfop_padrao = '5102' if idDest == '1' else '6102'
    dhEmi = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')

    itens = n.get('itens') or []
    if not itens:
        v_tot = float(n.get('valor') or 296.00)
        itens = [{'codigo': '001', 'nome': n.get('naturezaOperacao') or 'MERCADORIA', 'ncm': '49019900', 'cfop': cfop_padrao, 'un': 'UN', 'qtd': 1, 'valorUnit': v_tot}]

    dets_xml = ""
    vProd_total = 0.0
    for idx, it in enumerate(itens, 1):
        qtd = float(it.get('qtd') or 1)
        vUn = float(it.get('valorUnit') or it.get('preco') or 0)
        vProd = round(qtd * vUn, 2)
        vProd_total = round(vProd_total + vProd, 2)
        ncm = ''.join(filter(str.isdigit, str(it.get('ncm') or '49019900'))) or '49019900'
        cfop = ''.join(filter(str.isdigit, str(it.get('cfop') or cfop_padrao))) or cfop_padrao
        cProd = escape(str(it.get('codigo') or it.get('isbn') or idx)[:60])
        xProd = escape(str(it.get('nome') or it.get('titulo') or 'PRODUTO')[:120])
        uCom = escape(str(it.get('un') or 'UN')[:6])
        dets_xml += f'''<det nItem="{idx}">
          <prod>
            <cProd>{cProd}</cProd>
            <cEAN>SEM GTIN</cEAN>
            <xProd>{xProd}</xProd>
            <NCM>{ncm}</NCM>
            <CFOP>{cfop}</CFOP>
            <uCom>{uCom}</uCom>
            <qCom>{qtd:.4f}</qCom>
            <vUnCom>{vUn:.4f}</vUnCom>
            <vProd>{vProd:.2f}</vProd>
            <cEANTrib>SEM GTIN</cEANTrib>
            <uTrib>{uCom}</uTrib>
            <qTrib>{qtd:.4f}</qTrib>
            <vUnTrib>{vUn:.4f}</vUnTrib>
            <indTot>1</indTot>
          </prod>
          <imposto>
            <ICMS><ICMSSN102><orig>0</orig><CSOSN>102</CSOSN></ICMSSN102></ICMS>
            <PIS><PISNT><CST>07</CST></PISNT></PIS>
            <COFINS><COFINSNT><CST>07</CST></COFINSNT></COFINS>
          </imposto>
        </det>'''

    vFrete = float(n.get('valorFrete') or 0.0)
    vNF = round(vProd_total + vFrete, 2)
    doc_tag = f"<CNPJ>{cnpj_dest}</CNPJ>" if len(cnpj_dest) == 14 else (f"<CPF>{cnpj_dest}</CPF>" if len(cnpj_dest) == 11 else "<CNPJ>00000000000000</CNPJ>")
    cep_dest = ''.join(filter(str.isdigit, str(n.get('destCep') or '86730000'))).zfill(8)[:8]
    infCpl = escape(str(n.get('infoComplementar') or 'Documento emitido por ME ou EPP optante pelo Simples Nacional.'))

    xml_nfe = f'''<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
      <infNFe Id="NFe{chave}" versao="4.00">
        <ide>
          <cUF>41</cUF><cNF>{cNF}</cNF><natOp>{escape(str(n.get('naturezaOperacao') or 'Venda de Mercadoria')[:60])}</natOp>
          <mod>55</mod><serie>{int(serie)}</serie><nNF>{nNF_int}</nNF><dhEmi>{dhEmi}</dhEmi>
          <tpNF>1</tpNF><idDest>{idDest}</idDest><cMunFG>4102109</cMunFG><tpImp>1</tpImp>
          <tpEmis>1</tpEmis><cDV>{cDV}</cDV><tpAmb>1</tpAmb><finNFe>1</finNFe><indFinal>1</indFinal><indPres>1</indPres><procEmi>0</procEmi><verProc>ASBF-ERP-1.0</verProc>
        </ide>
        <emit>
          <CNPJ>02293109000190</CNPJ><xNome>ASBF REVISTAS TECNICAS INTERNACIONAIS LTDA</xNome><xFant>ASBF REVISTAS TECNICAS</xFant>
          <enderEmit><xLgr>Rua Antonio Tarifa Vargas</xLgr><nro>245</nro><xBairro>Jardim Sinuelo</xBairro><cMun>4102109</cMun><xMun>Astorga</xMun><UF>PR</UF><CEP>86730000</CEP><cPais>1058</cPais><xPais>BRASIL</xPais></enderEmit>
          <IE>9126075003</IE><CRT>1</CRT>
        </emit>
        <dest>
          {doc_tag}<xNome>{escape(str(n.get('cliente') or 'CLIENTE')[:60])}</xNome>
          <enderDest><xLgr>{escape(str(n.get('destEndereco') or 'Centro')[:60])}</xLgr><nro>SN</nro><xBairro>Centro</xBairro><cMun>4102109</cMun><xMun>{escape(dest_xMun[:60])}</xMun><UF>{dest_uf}</UF><CEP>{cep_dest}</CEP><cPais>1058</cPais><xPais>BRASIL</xPais></enderDest>
          <indIEDest>9</indIEDest>
        </dest>
        {dets_xml}
        <total>
          <ICMSTot>
            <vBC>0.00</vBC><vICMS>0.00</vICMS><vICMSDeson>0.00</vICMSDeson><vFCP>0.00</vFCP><vBCST>0.00</vBCST><vST>0.00</vST><vFCPST>0.00</vFCPST><vFCPSTRet>0.00</vFCPSTRet>
            <vProd>{vProd_total:.2f}</vProd><vFrete>{vFrete:.2f}</vFrete><vSeg>0.00</vSeg><vDesc>0.00</vDesc><vII>0.00</vII><vIPI>0.00</vIPI><vIPIDevol>0.00</vIPIDevol><vPIS>0.00</vPIS><vCOFINS>0.00</vCOFINS><vOutro>0.00</vOutro><vNF>{vNF:.2f}</vNF>
          </ICMSTot>
        </total>
        <transp><modFrete>{str(n.get('modalidadeFrete') or '0')[:1]}</modFrete></transp>
        <pag><detPag><tPag>15</tPag><vPag>{vNF:.2f}</vPag></detPag></pag>
        
        <infAdic><infCpl>{infCpl}</infCpl></infAdic>
      <infRespTec>
          <CNPJ>02293109000190</CNPJ>
          <xContato>Alexandre Soares de Brito</xContato>
          <email>asbfjournals@gmail.com</email>
          <fone>4431340329</fone>
        </infRespTec>
      </infNFe>
    </NFe>'''
    return chave, xml_nfe

@app.route('/api/nfe/emitir', methods=['POST'])
def emitir_nfe_sefaz():
    try:
        dados = request.get_json(force=True) or {}
        chave, xml_str = montar_xml_nfe_400(dados)
        with open(PFX_PATH, 'rb') as f:
            priv_key, cert, add_certs = pkcs12.load_key_and_certificates(f.read(), CERT_PASSWORD)
        cert_pem = cert.public_bytes(Encoding.PEM)
        key_pem = priv_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

        parser = LET.XMLParser(remove_blank_text=True)
        nfe_elem = LET.fromstring(xml_str.encode('utf-8'), parser)
        class NFeSigner(XMLSigner):
            def check_deprecated_methods(self): pass
        signer = NFeSigner(method=methods.enveloped, signature_algorithm='rsa-sha1', digest_algorithm='sha1', c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        signer.namespaces = {None: 'http://www.w3.org/2000/09/xmldsig#'}
        signed_nfe = signer.sign(nfe_elem, key=key_pem, cert=cert_pem, reference_uri=f"#NFe{chave}")
        for x509 in signed_nfe.iter('{http://www.w3.org/2000/09/xmldsig#}X509Certificate'):
            if x509.text: x509.text = x509.text.replace('\n', '').replace('\r', '').strip()
        signed_xml = LET.tostring(signed_nfe, encoding='utf-8').decode('utf-8')

        soap = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">
      <enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><idLote>1</idLote><indSinc>1</indSinc>{signed_xml}</enviNFe>
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''

        with tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as cf, tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as kf:
            cf.write(cert_pem)
            kf.write(key_pem)
            c_path, k_path = cf.name, kf.name

        resp = requests.post('https://nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4', data=soap.encode('utf-8'), headers={'Content-Type': 'application/soap+xml; charset=utf-8'}, cert=(c_path, k_path), verify=False, timeout=35)
        os.remove(c_path); os.remove(k_path)

        root = ET.fromstring(resp.text)
        cStat, xMotivo, nProt = '', '', ''
        for el in root.iter():
            if el.tag.endswith('cStat'): cStat = el.text
            elif el.tag.endswith('xMotivo'): xMotivo = el.text
            elif el.tag.endswith('nProt'): nProt = el.text

        return jsonify({"status": "ok" if cStat in ('100', '104') else "rejeicao", "cStat": cStat, "xMotivo": xMotivo, "protocolo": nProt, "chave": chave, "xmlAssinado": signed_xml, "soapResposta": resp.text[:1000]})
    except Exception as e:
        return jsonify({"status": "erro", "motivo": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5055))
    print(f"Iniciando ASBF SEFAZ Cloud Sync na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)









