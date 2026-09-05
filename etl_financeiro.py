import logging
import sqlite3
from datetime import datetime
from typing import Optional
import requests

# Configuração básica de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Constantes de configuração
DB_NAME = "sistema_precos.db"
API_URL = "https://economia.awesomeapi.com.br/last/USD-BRL"
REQUEST_TIMEOUT = 10  # segundos


def configurar_banco(db_path: str = DB_NAME) -> sqlite3.Connection:
    """Cria a conexão e a tabela relacional se não existirem."""
    conexao = sqlite3.connect(db_path)
    with conexao:
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS historico_precos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto TEXT NOT NULL,
                preco_brl REAL NOT NULL,
                preco_usd REAL NOT NULL,
                data_conversao TEXT NOT NULL
            )
        ''')
    return conexao


# --- 1. EXTRACT ---
def extrair_cotacao_dolar(url: str = API_URL) -> Optional[float]:
    """Busca a cotação do dólar na API pública de forma segura com timeout e tratamento de erros."""
    try:
        resposta = requests.get(url, timeout=REQUEST_TIMEOUT)
        resposta.raise_for_status()
        dados = resposta.json()
        bid_str = dados.get("USDBRL", {}).get("bid")
        if bid_str is not None:
            return float(bid_str)
        logging.error("Campo 'bid' não encontrado no payload retornado pela API.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao consultar a API de cotação: {e}")
    except (ValueError, TypeError) as e:
        logging.error(f"Erro ao converter cotação para float: {e}")
    return None


# --- 2. TRANSFORM ---
def transformar_precos(produtos: list[tuple[str, float]], cotacao_usd: float) -> list[tuple[str, float, float, str]]:
    """Calcula o valor em dólar para cada produto e adiciona timestamp."""
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    registros_transformados = []
    
    for nome, preco_brl in produtos:
        preco_usd = round(preco_brl / cotacao_usd, 2)
        registros_transformados.append((nome, preco_brl, preco_usd, data_atual))
        
    return registros_transformados


# --- 3. LOAD ---
def carregar_dados(conexao: sqlite3.Connection, registros: list[tuple[str, float, float, str]]) -> None:
    """Persiste os registros em lote dentro de uma transação segura com commit automático."""
    with conexao:
        conexao.executemany('''
            INSERT INTO historico_precos (produto, preco_brl, preco_usd, data_conversao)
            VALUES (?, ?, ?, ?)
        ''', registros)
    logging.info(f"{len(registros)} registros inseridos com sucesso no banco de dados.")


def exibir_historico(conexao: sqlite3.Connection) -> None:
    """Exibe os registros salvos de forma organizada."""
    cursor = conexao.cursor()
    cursor.execute("SELECT id, produto, preco_brl, preco_usd, data_conversao FROM historico_precos")
    registros = cursor.fetchall()
    
    print("\n--- HISTÓRICO DE PREÇOS NO BANCO ---")
    for reg in registros:
        print(f"ID: {reg[0]:<3} | Produto: {reg[1]:<32} | R$ {reg[2]:<8.2f} | $ {reg[3]:<8.2f} | Data: {reg[4]}")


def main():
    # Dados de entrada (podem vir futuramente de CSV, JSON ou outro BD)
    produtos = [
        ("Módulo Assistência Técnica", 2500.00),
        ("Integração Gateway de Pagamento", 4200.00)
    ]
    
    conexao = configurar_banco()
    try:
        cotacao = extrair_cotacao_dolar()
        if cotacao:
            logging.info(f"Cotação do Dólar obtida: R$ {cotacao:.4f}")
            dados_processados = transformar_precos(produtos, cotacao)
            carregar_dados(conexao, dados_processados)
        else:
            logging.warning("Processamento abortado: não foi possível obter a cotação do dólar.")
        
        exibir_historico(conexao)
    finally:
        conexao.close()


if __name__ == "__main__":
    main()