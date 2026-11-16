"""Comparáveis REAIS coletados para a validação do RESIDENCIAL AMERICA 5 (imóvel 7), em 16/11/2026.

Origem: páginas públicas de busca (ZAP Imóveis, Imovelweb) e resultados de busca que exibem anúncios do VivaReal. Os
portais bloquearam o acesso direto às páginas (HTTP 403) após a primeira consulta; os valores abaixo são os que
apareceram na consulta, sem complemento. São PREÇOS ANUNCIADOS (pedidos), não negócios fechados. Nomes de
corretores/imobiliárias foram omitidos. A URL é a da página de busca (a do anúncio individual não foi exposta).

Exclusões feitas na coleta (registradas, não apagadas):
- o próprio imóvel 7 aparece anunciado (R$ 132.970, Rua Macapá, 45 m², bairro Estados): excluído;
- anúncios repetidos por corretores diferentes (mesmo valor e área) são detectados pelo motor como duplicatas.
"""
from datetime import date
from decimal import Decimal

COLETA = date(2026, 11, 16)
ZAP_VENDA = "https://www.zapimoveis.com.br/venda/apartamentos/pr+fazenda-rio-grande/2-quartos/"
IW_VENDA = "https://www.imovelweb.com.br/apartamentos-venda-fazenda-rio-grande-pr.html"
VR_ALUGUEL_ESTADOS = "https://www.vivareal.com.br/aluguel/parana/fazenda-rio-grande/bairros/estados/"
VR_ALUGUEL_CHURRASQUEIRA = "https://www.vivareal.com.br/aluguel/parana/fazenda-rio-grande/com-churrasqueira/"

IMOVEL7 = {
    "title": "RESIDENCIAL AMERICA 5", "city": "Fazenda Rio Grande", "state": "PR", "neighborhood": "Estados", "property_type": "Apartamento",
    "address": "Rua Macapá", "area_m2": Decimal("48.74"), "private_area_m2": Decimal("45.50"),
    "bedrooms": 2, "parking_spots": 1, "modality": "VENDA_DIRETA", "origin": "CAIXA",
}

# Premissas do imóvel 7 (Auction.financial_assumptions): cada uma com a origem.
PREMISSAS_IMOVEL7 = {
    "itbi_aliquota": "0.025", "itbi_base_minima": "141825.75",
    "itbi_origem": "matrícula do imóvel (Av-5): ITBI de R$ 3.545,64 sobre R$ 141.825,75 (2,5%); alíquota vigente a confirmar na Prefeitura",
    "condicoes_caixa": {"condominio_limite_pct_avaliacao": "0.10", "tributos_limite_pct_avaliacao": "0.10", "origem": "condições da venda direta Caixa (anúncio do imóvel)"},
}


def _venda(ident, bairro, endereco, area, preco, *, cond=None, iptu=None, vagas=1, base="DESCONHECIDA", url=ZAP_VENDA, fonte="ZAP Imóveis (busca)", notas=None, excluido=False, motivo=None):
    return {"listing_ref": ident, "kind": "VENDA", "price": Decimal(preco), "area_m2": Decimal(area), "source": fonte, "url": url, "price_type": "ANUNCIADO",
            "collected_at": COLETA, "neighborhood": bairro, "address": endereco, "city": "Fazenda Rio Grande", "state": "PR", "property_type": "Apartamento",
            "bedrooms": 2, "parking_spots": vagas, "condo_fee": Decimal(cond) if cond is not None else None, "iptu": Decimal(iptu) if iptu is not None else None,
            "area_basis": base, "notes": notas, "excluded": excluido, "exclusion_reason": motivo}


COMPARAVEIS_VENDA = [
    _venda("zap-01", "Eucaliptos", "Avenida Venezuela", "42", "240000", cond="350", iptu="340"),
    _venda("zap-02", "Estados", "Rua Maranhão", "42", "180200", cond="340", iptu="20", vagas=0),
    _venda("zap-03", "Nações", "Avenida Venezuela", "43", "208000"),
    _venda("zap-04", "Nações", "Avenida Venezuela", "42", "208000", notas="Mesmo valor do zap-03, outro anunciante"),
    _venda("zap-05", "Eucaliptos", "Avenida Venezuela", "42", "200000"),
    _venda("zap-06", "Estados", "Rua Maranhão", "39", "215000", iptu="0", notas="IPTU informado como isento"),
    _venda("zap-07", "Santa Terezinha", "Avenida Nossa Senhora Aparecida", "42", "275560"),
    _venda("zap-08", "Estados", "Rua Macapá", "45", "132970", excluido=True, motivo="É o próprio imóvel analisado (anúncio Caixa)"),
    _venda("zap-09", "Eucaliptos", "Avenida Venezuela", "40", "244000", cond="0", iptu="1000", notas="Condomínio informado como isento"),
    _venda("zap-10", "Santa Terezinha", None, "42", "275560", notas="Mesmo valor do zap-07, endereço não informado"),
    _venda("zap-11", "Estados", "Rua Manaus", "46", "193001", notas="Valor quebrado típico de imóvel de banco; confirmar se é venda direta"),
    _venda("zap-12", "Estados", "Rua Manaus", "45", "193001", notas="Mesmo valor do zap-11, outro anunciante"),
    _venda("zap-13", "Eucaliptos", "Avenida Venezuela", "42", "210000", cond="393", iptu="415"),
    _venda("zap-14", "Santa Terezinha", None, "42", "240000", cond="250", iptu="50"),
    _venda("zap-15", "Estados", "Rua Macapá", "45", "132970", excluido=True, motivo="É o próprio imóvel analisado (anúncio Caixa, outro anunciante)"),
    _venda("iw-01", "Eucaliptos", None, "59", "210000", cond="350", base="TOTAL", url=IW_VENDA, fonte="Imovelweb (busca)", notas="Área total; 2º andar; salão de festas"),
    _venda("iw-02", "Iguaçu", "Rua Rio Piraí", "54", "300000", vagas=2, base="TOTAL", url=IW_VENDA, fonte="Imovelweb (busca)", notas="Área total; garden privativo; móveis planejados"),
    _venda("iw-03", "Santa Terezinha", "Avenida Nossa Senhora Aparecida, 2370", "56", "290000", cond="765", base="TOTAL", url=IW_VENDA, fonte="Imovelweb (busca)",
           notas="Área total; apartamento novo em condomínio clube (padrão superior)"),
]

COMPARAVEIS_ALUGUEL = [
    {"listing_ref": "vr-a01", "kind": "ALUGUEL", "price": Decimal("0"), "rent": Decimal("1200"), "area_m2": Decimal("45"), "source": "VivaReal (resultado de busca)",
     "url": VR_ALUGUEL_ESTADOS, "price_type": "ANUNCIADO", "collected_at": COLETA, "neighborhood": "Estados", "address": "Rua Maranhão", "city": "Fazenda Rio Grande",
     "state": "PR", "property_type": "Apartamento", "bedrooms": 2, "parking_spots": 1, "area_basis": "DESCONHECIDA",
     "notes": "Valor lido no resultado de busca (página indexada em 08/02/2025); o portal bloqueou o acesso direto; o anúncio pode não estar ativo."},
    {"listing_ref": "vr-a02", "kind": "ALUGUEL", "price": Decimal("0"), "rent": Decimal("1315"), "area_m2": Decimal("0"), "source": "VivaReal (resultado de busca)",
     "url": VR_ALUGUEL_CHURRASQUEIRA, "price_type": "ANUNCIADO", "collected_at": COLETA, "neighborhood": "Estados", "city": "Fazenda Rio Grande", "state": "PR",
     "property_type": "Apartamento", "notes": "Área e quartos não exibidos no resultado de busca; sem data do anúncio."},
]
