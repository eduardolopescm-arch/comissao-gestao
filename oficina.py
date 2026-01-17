import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- BANCO DE DADOS ---
def iniciar_db():
    conn = sqlite3.connect('financeiro_oficina.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS colaboradores (id INTEGER PRIMARY KEY, nome TEXT, senha TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                 (id INTEGER PRIMARY KEY, colaborador TEXT, tipo TEXT, 
                  valor_base REAL, porcentagem REAL, valor_final REAL, 
                  descricao TEXT, data TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historico 
                 (id INTEGER PRIMARY KEY, colaborador TEXT, tipo TEXT, 
                  valor_base REAL, porcentagem REAL, valor_final REAL, 
                  descricao TEXT, data TEXT, data_fechamento TEXT)''')
    conn.commit()
    conn.close()

iniciar_db()

st.set_page_config(page_title="Gestão Financeira Oficina", layout="wide")

# --- SIDEBAR ACESSO ---
st.sidebar.title("🔐 Acesso ao Sistema")
perfil = st.sidebar.radio("Perfil:", ["Colaborador (Visualizar)", "Administrador (Gestão)"])

if perfil == "Administrador (Gestão)":
    senha_adm = st.sidebar.text_input("Senha de Admin", type="password")
    if senha_adm != "134588":
        st.warning("Aguardando senha de administrador...")
        st.stop()

st.title(f"💰 Painel {perfil}")

# --- LÓGICA ADMINISTRADOR ---
if perfil == "Administrador (Gestão)":
    aba1, aba2, aba3, aba4 = st.tabs(["📝 Lançamentos", "📊 Relatório Completo", "👥 Equipe", "🗄️ Arquivo Morto"])
    
    with aba3:
        st.subheader("Gerenciar Equipe")
        c_nome, c_senha = st.columns(2)
        novo_colab = c_nome.text_input("Nome do Colaborador")
        senha_novo_colab = c_senha.text_input("Definir Senha do Colaborador", type="password")
        
        if st.button("Salvar Colaborador"):
            if novo_colab and senha_novo_colab:
                conn = sqlite3.connect('financeiro_oficina.db')
                conn.execute('INSERT INTO colaboradores (nome, senha) VALUES (?, ?)', (novo_colab, senha_novo_colab))
                conn.commit()
                conn.close()
                st.success(f"Colaborador {novo_colab} cadastrado!")
            else: st.error("Preencha todos os campos!")

    with aba1:
        conn = sqlite3.connect('financeiro_oficina.db')
        lista_colab = pd.read_sql_query("SELECT nome FROM colaboradores", conn)['nome'].tolist()
        conn.close()

        if lista_colab:
            col1, col2 = st.columns(2)
            with col1:
                colab_sel = st.selectbox("Selecione o Colaborador", lista_colab)
                tipo = st.radio("Tipo de Lançamento", ["Comissão", "Vale"])
            with col2:
                if tipo == "Comissão":
                    v_base = st.number_input("Valor Total do Serviço (R$)", min_value=0.0)
                    perc = st.number_input("Sua Margem (%)", value=10.0)
                    v_final = (v_base * perc) / 100
                    st.info(f"Comissão: R$ {v_final:.2f}")
                else:
                    v_final = st.number_input("Valor do Vale (R$)", min_value=0.0)
                    v_base, perc = v_final, 100
                desc = st.text_input("Descrição / Ref. OS")
            
            if st.button("Confirmar Lançamento"):
                hoje = datetime.now().strftime("%d/%m/%Y")
                conn = sqlite3.connect('financeiro_oficina.db')
                conn.execute("INSERT INTO lancamentos (colaborador, tipo, valor_base, porcentagem, valor_final, descricao, data) VALUES (?,?,?,?,?,?,?)",
                             (colab_sel, tipo, v_base, perc, v_final, desc, hoje))
                conn.commit()
                conn.close()
                st.success("Registrado com sucesso!")

    with aba2:
        st.subheader("📊 Fechamento Semanal Completo")
        conn = sqlite3.connect('financeiro_oficina.db')
        df = pd.read_sql_query("SELECT * FROM lancamentos", conn)
        conn.close()

        if not df.empty:
            # --- BLOCO DE MÉTRICAS GERAIS ---
            total_servicos = df[df['tipo'] == 'Comissão']['valor_base'].sum()
            total_comissoes = df[df['tipo'] == 'Comissão']['valor_final'].sum()
            total_vales = df[df['tipo'] == 'Vale']['valor_final'].sum()
            lucro_oficina = total_servicos - total_comissoes

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Faturamento (Serviços)", f"R$ {total_servicos:.2f}")
            m2.metric("Total Comissões", f"R$ {total_comissoes:.2f}")
            m3.metric("Total Vales", f"R$ {total_vales:.2f}")
            m4.metric("Saldo Oficina", f"R$ {lucro_oficina:.2f}")

            st.divider()

            # --- RESUMO POR COLABORADOR ---
            st.write("### 👥 Saldo por Colaborador")
            resumo_data = []
            colabs_unicos = df['colaborador'].unique()
            for c in colabs_unicos:
                df_c = df[df['colaborador'] == c]
                com = df_c[df_c['tipo'] == 'Comissão']['valor_final'].sum()
                val = df_c[df_c['tipo'] == 'Vale']['valor_final'].sum()
                resumo_data.append({"Colaborador": c, "Comissões": com, "Vales": val, "Líquido a Pagar": com - val})
            
            st.table(pd.DataFrame(resumo_data))

            st.divider()
            
            # --- FILTROS E TABELA DETALHADA ---
            st.write("### 📝 Detalhamento dos Lançamentos")
            filtro_c = st.multiselect("Filtrar Colaborador:", colabs_unicos, default=colabs_unicos)
            df_filtrado = df[df['colaborador'].isin(filtro_c)]
            st.dataframe(df_filtrado, use_container_width=True)

            if st.button("✅ Finalizar Semana e Arquivar Tudo"):
                hoje_f = datetime.now().strftime("%d/%m/%Y %H:%M")
                conn = sqlite3.connect('financeiro_oficina.db')
                conn.execute(f"INSERT INTO historico (colaborador, tipo, valor_base, porcentagem, valor_final, descricao, data, data_fechamento) SELECT colaborador, tipo, valor_base, porcentagem, valor_final, descricao, data, '{hoje_f}' FROM lancamentos")
                conn.execute("DELETE FROM lancamentos")
                conn.commit()
                conn.close()
                st.success("Semana finalizada e dados movidos para o arquivo morto!")
                st.rerun()
        else:
            st.info("Nenhum lançamento ativo para gerar relatório.")

    with aba4:
        st.subheader("🗄️ Arquivo Morto")
        conn = sqlite3.connect('financeiro_oficina.db')
        df_hist = pd.read_sql_query("SELECT * FROM historico ORDER BY id DESC", conn)
        conn.close()
        if not df_hist.empty:
            busca = st.text_input("Pesquisar no histórico...")
            if busca:
                df_hist = df_hist[df_hist.apply(lambda r: busca.lower() in str(r).lower(), axis=1)]
            st.dataframe(df_hist, use_container_width=True)

# --- LÓGICA COLABORADOR ---
else:
    st.subheader("🔍 Espaço do Colaborador")
    conn = sqlite3.connect('financeiro_oficina.db')
    colabs_db = pd.read_sql_query("SELECT * FROM colaboradores", conn)
    conn.close()
    
    lista_nomes = colabs_db['nome'].tolist()
    meu_nome = st.selectbox("Selecione seu nome", [""] + lista_nomes)
    
    if meu_nome:
        senha_digitada = st.text_input("Digite sua senha pessoal", type="password")
        senha_correta = colabs_db[colabs_db['nome'] == meu_nome]['senha'].values[0]
        
        if senha_digitada == str(senha_correta):
            conn = sqlite3.connect('financeiro_oficina.db')
            df_meu = pd.read_sql_query(f"SELECT tipo, valor_final, descricao, data FROM lancamentos WHERE colaborador = '{meu_nome}'", conn)
            conn.close()
            
            if not df_meu.empty:
                st.table(df_meu)
                comissoes = df_meu[df_meu['tipo'] == 'Comissão']['valor_final'].sum()
                vales = df_meu[df_meu['tipo'] == 'Vale']['valor_final'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("Comissões", f"R$ {comissoes:.2f}")
                c2.metric("Vales", f"R$ {vales:.2f}")
                c3.metric("A Receber", f"R$ {comissoes - vales:.2f}")
            else:
                st.info("Você não tem lançamentos pendentes nesta semana.")
        elif senha_digitada != "":
            st.error("Senha incorreta!")