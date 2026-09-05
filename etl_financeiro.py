import sqlite3
import requests
from datetime import datetime

def configurar_banco():
    """Cria a conexão e a tabela relacional se não existirem."""
    conexao = sqlite3.connect("sistema_precos.db")
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT,
            preco_brl REAL,
            preco_usd REAL,
            data_conversao TEXT
        )
    ''')
    conexao.commit()
    return conexao

def extrair_cotacao_dolar():
    """Busca a cotação do dólar na API pública."""
    resposta = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL")
    if resposta.status_code == 200:
        return float(resposta.json()["USDBRL"]["bid"])
    return None

def processar_e_salvar(conexao, cotacao_usd):
    """Aplica regra de conversão e persiste os dados via SQL."""
    produtos = [
        ("Módulo Assistência Técnica", 2500.00),
        ("Integração Gateway de Pagamento", 4200.00)
    ]
    
    cursor = conexao.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for nome, preco_brl in produtos:
        preco_usd = round(preco_brl / cotacao_usd, 2)
        cursor.execute('''
            INSERT INTO historico_precos (produto, preco_brl, preco_usd, data_conversao)
            VALUES (?, ?, ?, ?)
        ''', (nome, preco_brl, preco_usd, data_atual))
        print(f"✅ {nome} inserido no BD: R$ {preco_brl} -> $ {preco_usd}")
    
    conexao.commit()

# Execução do Script
conexao_bd = configurar_banco()
dolar_hoje = extrair_cotacao_dolar()

if dolar_hoje:
    processar_e_salvar(conexao_bd, dolar_hoje)

# Validação: Consultando o banco
print("\n--- REGISTROS NO BANCO DE DADOS ---")
for linha in conexao_bd.cursor().execute("SELECT * FROM historico_precos"):
    print(linha)

conexao_bd.close()