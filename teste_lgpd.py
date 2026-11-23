"""
Testes do motor LGPD. Usa apenas dados FICTÍCIOS e não acessa rede.

Uso:
    python3 teste_lgpd.py
"""
import unittest

import pandas as pd

from lgpd_engine import (
    anonimizar_dataframe,
    mascarar_apolice_proposta,
    mascarar_email,
    mascarar_nome,
    mascarar_telefone,
    somente_digitos,
)

# Valores-sentinela: se qualquer um aparecer na saída, houve vazamento.
SENTINELAS = {
    "nome_cliente": "Maria Fulana Testeira",
    "segurado": "Joao Beltrano Exemplo",
    "condutor": "Pedro Ciclano Demo",
    "corretor": "Marcos Fictício Silva",
    "cpf_cnpj": "123.456.789-09",
    "rg": "12.345.678-9",
    "telefone": "(11) 98765-4321",
    "celular_2": "+55 11 98765-1234",
    "email": "maria.testeira@exemplo.invalido",
    "numero_apólice": "9988776655443",
    "numero_apolice": "1122334455667",
    "numero_proposta": "5544332211",
    "placa_veiculo": "QWE1R23",
    "chassi": "9BWZZZ377VT004251",
    "renavam": "12345678901",
    "endereco": "Rua das Flores Imaginarias, 100",
    "cep": "01001-000",
    "data_nascimento": "1980-02-03",
    "banco": "341",
    "agencia": "8642",
    "conta": "55555-6",
    "pix": "chave.pix.ficticia@exemplo.invalido",
    "descricao": "cliente fará cirurgia amanhã",
    "comentario": "ligar para a esposa",
    "observacoes": "texto livre sensível",
    "coluna_nova_desconhecida": "valor que ninguém previu",
}

PUBLICAS = {
    "tipo_seguro": "Auto",
    "seguradora": "Seguradora Exemplo",
    "data_vencimento": "2026-12-01",
    "valor_premio": 2500.0,
}


class TesteTelefone(unittest.TestCase):
    def test_formatos_comuns(self):
        self.assertEqual(mascarar_telefone("(11) 98765-4321"), "(11) 9****-4321")
        self.assertEqual(mascarar_telefone("1134567890"), "(11) ****-7890")

    def test_ddi_55_nao_vaza_digitos_extras(self):
        # Antes da correção, 13 dígitos (DDI 55) saíam como "(55) ****-7654321".
        esperado = {
            "+55 11 98765-4321": "(11) 9****-4321",
            "5511987654321": "(11) 9****-4321",
            "+55 11 3456-7890": "(11) ****-7890",
        }
        for bruto, mascarado in esperado.items():
            self.assertEqual(mascarar_telefone(bruto), mascarado)

    def test_telefone_lido_como_float_pelo_pandas(self):
        # Coluna numérica com células vazias: o pandas entrega 11999998888.0.
        self.assertEqual(mascarar_telefone(11999998888.0), "(11) 9****-8888")
        self.assertEqual(somente_digitos(11999998888.0), "11999998888")

    def test_formato_desconhecido_nao_revela_nada(self):
        self.assertEqual(mascarar_telefone("12345"), "(**) ****-****")
        self.assertEqual(mascarar_telefone("1234567890123456"), "(**) ****-****")


class TesteMascarasBasicas(unittest.TestCase):
    def test_nome(self):
        self.assertEqual(mascarar_nome("Maria Fulana Testeira"), "M*** F*** T***")

    def test_email(self):
        self.assertEqual(mascarar_email("maria@exemplo.invalido"), "m***@exemplo.invalido")
        self.assertEqual(mascarar_email("sem-arroba"), "***@***")

    def test_apolice_mantem_so_ultimos_quatro(self):
        self.assertEqual(mascarar_apolice_proposta("1234567890"), "******7890")


class TesteAnonimizacao(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([{**SENTINELAS, **PUBLICAS}])
        self.saida = anonimizar_dataframe(self.df)

    def test_nenhum_dado_pessoal_sai_em_claro(self):
        texto = " | ".join(str(v) for v in self.saida.iloc[0].tolist())
        for coluna, valor in SENTINELAS.items():
            self.assertNotIn(str(valor), texto, f"coluna {coluna} vazou")

    def test_colunas_com_acento_e_desconhecidas_sao_cobertas(self):
        self.assertNotEqual(self.saida.loc[0, "numero_apólice"], SENTINELAS["numero_apólice"])
        self.assertEqual(self.saida.loc[0, "coluna_nova_desconhecida"], "[TEXTO REMOVIDO - LGPD]")

    def test_colunas_publicas_passam(self):
        for coluna, valor in PUBLICAS.items():
            self.assertEqual(self.saida.loc[0, coluna], valor)

    def test_nao_altera_o_dataframe_original(self):
        self.assertEqual(self.df.loc[0, "nome_cliente"], SENTINELAS["nome_cliente"])

    def test_cabecalho_nao_textual_nao_quebra(self):
        saida = anonimizar_dataframe(pd.DataFrame([[1, "x"]], columns=[0, 1]))
        self.assertEqual(list(saida.iloc[0]), ["[TEXTO REMOVIDO - LGPD]"] * 2)

    def test_nao_mascara_por_engano_colunas_curtas(self):
        # "margem" contém "rg", mas não é RG: é coluna desconhecida e sai removida, não como RG.
        saida = anonimizar_dataframe(pd.DataFrame([{"margem": "10%"}]))
        self.assertNotEqual(saida.loc[0, "margem"], "**.***.***-*")

    def test_texto_livre_em_coluna_publica_perde_dado_pessoal(self):
        saida = anonimizar_dataframe(pd.DataFrame([{
            "franquia": "nome: Joao CPF 111.222.333-44 tel (11) 98765-4321 a@exemplo.invalido",
            "modelo_veiculo": "Civic 2020 placa ABC1D23",
            "valor_premio": "1500,50",
        }]))
        texto = " ".join(str(v) for v in saida.iloc[0])
        for proibido in ("111.222.333-44", "98765-4321", "a@exemplo.invalido", "ABC1D23"):
            self.assertNotIn(proibido, texto)
        self.assertEqual(saida.loc[0, "valor_premio"], "1500,50")
        self.assertIn("Civic 2020", texto)

    def test_formula_do_excel_em_coluna_publica_e_neutralizada(self):
        saida = anonimizar_dataframe(pd.DataFrame([{
            "tipo_seguro": '=HYPERLINK("http://exemplo.invalido","x")',
            "seguradora": "@SUM(1+1)",
            "valor_premio": "-150,00",
        }]))
        self.assertTrue(saida.loc[0, "tipo_seguro"].startswith("'="))
        self.assertTrue(saida.loc[0, "seguradora"].startswith("'@"))
        self.assertEqual(saida.loc[0, "valor_premio"], "-150,00")  # número negativo legítimo


if __name__ == "__main__":
    unittest.main(verbosity=2)
