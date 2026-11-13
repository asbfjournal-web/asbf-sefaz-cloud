
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
            <ICMS><ICMSSN300><orig>0</orig><CSOSN>300</CSOSN></ICMSSN300></ICMS>
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
          <tpNF>1</tpNF><idDest>{idDest}</idDest><cMunFG>4102100</cMunFG><tpImp>1</tpImp>
          <tpEmis>1</tpEmis><cDV>{cDV}</cDV><tpAmb>1</tpAmb><finNFe>1</finNFe><indFinal>1</indFinal><indPres>1</indPres><procEmi>0</procEmi><verProc>ASBF-ERP-1.0</verProc>
        </ide>
        <emit>
          <CNPJ>02293109000190</CNPJ><xNome>ASBF REVISTAS TECNICAS INTERNACIONAIS LTDA</xNome><xFant>ASBF REVISTAS TECNICAS</xFant>
          <enderEmit><xLgr>Rua Antonio Tarifa Vargas</xLgr><nro>245</nro><xBairro>Jardim Sinuelo</xBairro><cMun>4102100</cMun><xMun>Astorga</xMun><UF>PR</UF><CEP>86730000</CEP><cPais>1058</cPais><xPais>BRASIL</xPais></enderEmit>
          <IE>9126075003</IE><CRT>1</CRT>
        </emit>
        <dest>
          {doc_tag}<xNome>{escape(str(n.get('cliente') or 'CLIENTE')[:60])}</xNome>
          <enderDest><xLgr>{escape(str(n.get('destEndereco') or 'Centro')[:60])}</xLgr><nro>SN</nro><xBairro>Centro</xBairro><cMun>4102100</cMun><xMun>{escape(dest_xMun[:60])}</xMun><UF>{dest_uf}</UF><CEP>{cep_dest}</CEP><cPais>1058</cPais><xPais>BRASIL</xPais></enderDest>
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
        signer = XMLSigner(method=methods.enveloped, signature_algorithm='rsa-sha1', digest_algorithm='sha1', c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        signed_nfe = signer.sign(nfe_elem, key=key_pem, cert=cert_pem, reference_uri=f"#NFe{chave}")
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

        resp = requests.post('https://nfe.sefaz.pr.gov.br/nfe/NFeAutorizacao4', data=soap.encode('utf-8'), headers={'Content-Type': 'application/soap+xml; charset=utf-8'}, cert=(c_path, k_path), timeout=35)
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
