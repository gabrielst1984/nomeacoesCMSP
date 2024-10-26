from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from datetime import datetime
import pandas as pd
import time

def check_strings_exist(main_string, substrings):
    for substring in substrings:
        if substring not in main_string:
            return False  # Retorna False se uma das substrings não for encontrada
    return True  # Retorna True se todas as substrings forem encontradas

# Set up Chrome options for headless mode
chrome_options = Options()
chrome_options.add_argument("--headless")  # Enable headless mode
chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
chrome_options.add_argument("--window-size=1920x1080")  # Set window size

# Configura o caminho do driver do navegador
url = "https://sei.prefeitura.sp.gov.br/sei/modulos/pesquisa/md_pesq_processo_exibir.php?XJe606xoyp3QxxkeXOtNa0fx5PPdOBVgkXyyCkRr268Y7xoi5fMBgzr21Gi2DD48HqC6CR8GlHl6lm-9YjSC5xE15l8KT5q5ATb3_mhXwd6GcusHK1LjH4MzBpWwclPI"
# Strings a serem buscadas
busca_geral = "integrante do Quadro do Pessoal do Legislativo, Anexo I da Lei nº 13.637/03, alterado pelo Anexo II da Lei nº 14.381/07 e suas alterações posteriores. (Processo nº 75/2023)."
busca_sem_efeito = "TORNANDO sem efeito a Portaria"
busca_nomeacao1 = "NOMEANDO "
busca_nomeacao2 = ", tendo em vista a classificação obtida em concurso público, publicada no Diário Oficial da Cidade de São Paulo de"

eventosSet = set()

service = Service()
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Acessa a página
    driver.get(url)

    # Pausa para carregar (ajuste conforme necessário)
    time.sleep(1)

    # Data de hoje no formato que aparece na tabela (ajuste se necessário)
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    #data_hoje = datetime(2024, 10, 25).strftime("%d/%m/%Y")

    # Encontra a tabela com id 'tblDocumentos'
    tabela = driver.find_element(By.ID, "tblDocumentos")

    # Encontra todas as linhas na tabela
    linhas = tabela.find_elements(By.TAG_NAME, "tr")

    # Itera sobre as linhas e verifica a quarta coluna
    for linha in linhas:
        colunas = linha.find_elements(By.TAG_NAME, "td")

        # Verifica se a linha tem pelo menos quatro colunas
        if len(colunas) >= 4:
            data_coluna = colunas[3].text  # Quarta coluna é o índice 3
            # Compara com a data de hoje
            if data_coluna == data_hoje:

                # Encontra todos os elementos <a>
                links = colunas[1].find_elements(By.TAG_NAME, "a")

                for link in links:
                    driver.execute_script(f"{link.get_attribute('onclick')};")

                    # Pausa para garantir que a nova aba ou janela foi aberta
                    time.sleep(1)

                    # Muda o foco para a nova aba/janela (a última que foi aberta)
                    driver.switch_to.window(driver.window_handles[-1])

                    # Encontra todos os elementos <p>
                    ps = driver.find_elements(By.TAG_NAME, "p")

                    # Itera sobre os ps e verifica se a string está presente
                    for p in ps:
                        if check_strings_exist(p.text, [busca_geral, busca_sem_efeito]) or check_strings_exist(p.text, [busca_geral, busca_nomeacao1, busca_nomeacao2]) :
                            eventosSet.add(p.text)

                    # Fecha a aba atual
                    driver.close()

                    # Retorna à aba principal (a primeira que foi aberta)
                    driver.switch_to.window(driver.window_handles[0])

    eventosList = sorted(eventosSet)
    df = pd.DataFrame(eventosList)

    if not df.empty:
        df_nomeacao    = df[df.iloc[:, 0].str.startswith(busca_nomeacao1)]
        if not df_nomeacao.empty:
            df_nomeacao.iloc[:, 0] = df_nomeacao.iloc[:, 0].str.replace(busca_nomeacao1, '', regex=False)
            df_nomeacao.iloc[:, 0] = df_nomeacao.iloc[:, 0].str.replace(busca_nomeacao2, '|', regex=False)
            df_nomeacao.iloc[:, 0] = df_nomeacao.iloc[:, 0].str.replace(", para exercer o cargo de ", '|', regex=False)
            df_nomeacao.iloc[:, 0] = df_nomeacao.iloc[:, 0].str.replace(", referência QPL-", '|', regex=False)

            df_nomeacao         = df_nomeacao.iloc[:, 0].str.split('|', expand=True)
            df_nomeacao         = df_nomeacao.drop([1, 3], axis=1, errors='ignore')
            df_nomeacao.columns = ['Nome Completo', 'Cargo / Especialidade']
            df_nomeacao['Evento'] = 'Nomeação'

        df_sem_efeito = df[df[0].str.startswith(busca_sem_efeito)]
        if not df_sem_efeito.empty:
            df_sem_efeito.iloc[:, 0] = df_sem_efeito.iloc[:, 0].str.replace(", que nomeou ", '|', regex=False)
            df_sem_efeito.iloc[:, 0] = df_sem_efeito.iloc[:, 0].str.replace(", para exercer o cargo de ", '|', regex=False)
            df_sem_efeito.iloc[:, 0] = df_sem_efeito.iloc[:, 0].str.replace(", referência QPL-", '|', regex=False)

            df_sem_efeito         = df_sem_efeito.iloc[:, 0].str.split('|', expand=True)
            df_sem_efeito         = df_sem_efeito.drop([0, 3], axis=1, errors='ignore')
            df_sem_efeito.columns = ['Nome Completo', 'Cargo / Especialidade']
            df_sem_efeito['Evento'] = 'Nomeação Sem Efeito'

        if not df_nomeacao.empty and not df_sem_efeito.empty:
            df = pd.concat([df_nomeacao, df_sem_efeito], ignore_index=True)
            df['Data SEI'] = data_hoje
            df = df[['Data SEI', 'Evento', 'Nome Completo', 'Cargo / Especialidade']]
            html_table = df.to_html(index=False)
            with open("index.html", "w") as file:
                file.write(html_table)
        elif not df_nomeacao.empty:
            df = df_nomeacao
            df['Data SEI'] = data_hoje
            df = df[['Data SEI', 'Evento', 'Nome Completo', 'Cargo / Especialidade']]
            html_table = df.to_html(index=False)
            with open("index.html", "w") as file:
                file.write(html_table)
        elif not df_sem_efeito.empty:
            df = df_sem_efeito
            df['Data SEI'] = data_hoje
            df = df[['Data SEI', 'Evento', 'Nome Completo', 'Cargo / Especialidade']]
            html_table = df.to_html(index=False)
            with open("index.html", "w") as file:
                file.write(html_table)

finally:
    # Fecha o navegador
    driver.quit()