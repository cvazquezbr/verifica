# WP Plugin Monitor - tagDiv Composer

Esta aplicação monitora o status do plugin **tagDiv Composer** em um site WordPress a cada minuto. Caso o plugin seja desativado, a aplicação tenta reativá-lo automaticamente via REST API do WordPress.

## Requisitos Prévios

1.  **Python 3.10+** instalado.
2.  **Application Password** do WordPress:
    -   No seu painel WordPress, vá em *Usuários > Perfil*.
    -   Role até a seção "Senhas de aplicativos".
    -   Crie uma nova senha para esta aplicação.

## Instalação e Configuração

1.  **Clone o repositório:**
    ```bash
    git clone <url-do-repositorio>
    cd <diretorio-do-projeto>
    ```

2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    # No Windows:
    .\venv\Scripts\activate
    # No Linux/Mac:
    source venv/bin/activate
    ```

3.  **Instale os pacotes necessários:**
    ```bash
    pip install -r requirements.txt
    ```

## Como Executar

Para iniciar a aplicação em modo de desenvolvimento:
```bash
python app.py
```

## Como Gerar o Executável (.exe para Windows)

Para compilar a aplicação em um único arquivo executável:

1.  Certifique-se de estar com o ambiente virtual ativado e as dependências instaladas.
2.  Execute o comando:
    ```bash
    pyinstaller --noconsole --onefile --collect-all customtkinter --name "WPMonitor" app.py
    ```
3.  O executável será gerado na pasta `dist/WPMonitor.exe`.

*Nota: O `--collect-all customtkinter` é necessário para garantir que todos os temas e arquivos JSON do CustomTkinter sejam incluídos no executável.*

## Funcionalidades

-   **Dashboard:** Inicia/Para o monitoramento e exibe logs em tempo real.
-   **Configurações:** Cadastro da URL do site e credenciais (Application Password).
-   **Estatísticas:** Gráficos de disponibilidade por hora (visão diária) e por dia (visão mensal).
-   **Armazenamento:** Os dados são salvos localmente em um banco de dados SQLite (`monitor.db`).
