import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- BAZA DE DATE ---
def init_db():
    conn = sqlite3.connect('lentis_optic_v26.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS locatii
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nume_locatie TEXT, adresa TEXT, contact TEXT, tel TEXT, note TEXT, data TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clienti
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, id_locatie INTEGER, nume TEXT, varsta INTEGER, tel TEXT,
                  tip_l TEXT, nume_lentila TEXT, regim TEXT, sf_od TEXT, cl_od TEXT, ax_od TEXT, sf_os TEXT, cl_os TEXT, ax_os TEXT,
                  addit TEXT, dp TEXT, rama TEXT, p_rama REAL, p_lent REAL, total REAL,
                  status TEXT, data_comanda TEXT, data_livrare TEXT, note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS plati
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, id_client INTEGER, suma REAL, data TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS utilizatori
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, rol TEXT)''')
    try:
        c.execute("INSERT INTO utilizatori (username, password, rol) VALUES (?,?,?)", ("admin", "lentis2024", "Admin"))
    except: pass
    conn.commit()
    return conn

st.set_page_config(page_title="Lentis Optic CRM Pro", layout="wide")

# --- FUNCTIE CULOARE STATUS ---
def color_status(val):
    colors = {
        "Comandă Nouă": "background-color: #000000; color: white;",
        "Comandată": "background-color: #007bff; color: white;",
        "Livrată + Rate": "background-color: #28a745; color: white;",
        "Finalizată": "background-color: #155724; color: white;",
        "Problemă": "background-color: #dc3545; color: white;"
    }
    return colors.get(val, "")

# --- STATE ---
if 'auth' not in st.session_state: st.session_state['auth'] = False
if 'user_rol' not in st.session_state: st.session_state['user_rol'] = None
if 'selected_client_id' not in st.session_state: st.session_state['selected_client_id'] = None
if 'ultima_locatie_index' not in st.session_state: st.session_state['ultima_locatie_index'] = 0

# --- LOGIN ---
if not st.session_state['auth']:
    st.title("🔐 Login Lentis Optic")
    with st.form("login"):
        u = st.text_input("Utilizator"); p = st.text_input("Parolă", type="password")
        if st.form_submit_button("Conectare"):
            conn = init_db()
            user = conn.execute("SELECT rol FROM utilizatori WHERE username=? AND password=?", (u, p)).fetchone()
            conn.close()
            if user:
                st.session_state['auth'] = True; st.session_state['user_rol'] = user[0]; st.rerun()
            else: st.error("Date incorecte!")
    st.stop()

conn = init_db()
is_admin = st.session_state['user_rol'] == "Admin"

# --- MENIU SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state['user_rol']}")
menu = ["📍 Locații & Statistici", "👥 Adaugă Client", "📋 Tabel Plăți & Fișe"]
if is_admin: menu.append("🛡️ Administrare Useri")
choice = st.sidebar.selectbox("Meniu", menu)

if st.sidebar.button("Deconectare"):
    st.session_state['auth'] = False; st.rerun()

# --- 1. LOCAȚII ---
if choice == "📍 Locații & Statistici":
    st.header("🏢 Gestiune Locații")
    with st.expander("➕ Adaugă Locație Nouă"):
        with st.form("f_loc"):
            c1, c2 = st.columns(2)
            n, adr = c1.text_input("Nume Locație *"), c1.text_area("Adresă *")
            pc, tl = c2.text_input("Persoană Contact *"), c2.text_input("Telefon *")
            nt = st.text_area("Note Locație (Opțional)")
            if st.form_submit_button("Salvează Locația"):
                if n and adr and pc and tl:
                    conn.execute("INSERT INTO locatii (nume_locatie, adresa, contact, tel, note, data) VALUES (?,?,?,?,?,?)", (n, adr, pc, tl, nt, datetime.now().strftime("%d-%m-%Y")))
                    conn.commit(); st.success("Salvat!"); st.rerun()
                else: st.error("⚠️ Completează câmpurile cu *")

    loc_df = pd.read_sql_query("SELECT * FROM locatii", conn)
    if not loc_df.empty:
        sel_loc = st.selectbox("Alege Locația:", loc_df['nume_locatie'])
        id_loc = loc_df[loc_df['nume_locatie'] == sel_loc]['id'].values[0]
        stats = pd.read_sql_query(f"SELECT COUNT(id) as nr, SUM(total) as suma FROM clienti WHERE id_locatie = {id_loc}", conn).iloc[0]
        m1, m2 = st.columns(2)
        m1.metric("Număr Clienți", f"{stats['nr'] or 0}")
        m2.metric("Valoare Totală", f"{(stats['suma'] or 0):,.2f} RON")

# --- 2. ADĂUGARE CLIENȚI ---
elif choice == "👥 Adaugă Client":
    st.header("👤 Fișă Pacient Nou")
    loc_df = pd.read_sql_query("SELECT id, nume_locatie FROM locatii", conn)
    if not loc_df.empty:
        n_loc = list(loc_df['nume_locatie'])
        l_sel = st.selectbox("🔍 Locație *:", n_loc, index=st.session_state['ultima_locatie_index'])
        st.session_state['ultima_locatie_index'] = n_loc.index(l_sel)
        id_l = int(loc_df[loc_df['nume_locatie'] == l_sel]['id'].values[0])
       
        with st.form("f_cli", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            nume, tel = c1.text_input("Nume Complet *"), c1.text_input("Telefon *")
            tl, nl = c2.selectbox("Tip Lentilă *", ["Monofocal", "Progresiv", "Degressiv"]), c2.text_input("Model Lentilă *")
            rama, pr, pl = c3.text_input("Model Ramă *"), c3.number_input("Preț Ramă *", value=0.0), c3.number_input("Preț Lentile *", value=0.0)
            st.divider(); d_col1, d_col2 = st.columns(2); data_c, data_l = d_col1.date_input("Data Comandă *", datetime.now()), d_col2.date_input("Data Livrare *", datetime.now())
            st.divider(); st.write("👓 **Dioptrii (Opțional)**")
            d1,d2,d3,d4,d5,d6 = st.columns([1,2,2,2,2,2]); d1.write("**OD**\n\n**OS**")
            sod, sos = d2.text_input("Sf OD"), d2.text_input("Sf OS"); cod, cos = d3.text_input("Cil OD"), d3.text_input("Cil OS")
            aod, aos = d4.text_input("Ax OD"), d4.text_input("Ax OS"); add, dp = d5.text_input("Adiție"), d6.text_input("DP")
            note_p = st.text_area("Note (Opțional)")
           
            if st.form_submit_button("✅ SALVEAZĂ"):
                errs = [k for k, v in {"Nume": nume, "Tel": tel, "Lentilă": nl, "Ramă": rama}.items() if not v]
                if not errs and (pr+pl) > 0:
                    conn.execute('''INSERT INTO clienti (id_locatie, nume, tel, tip_l, nume_lentila, sf_od, cl_od, ax_od, sf_os, cl_os, ax_os, addit, dp, rama, p_rama, p_lent, total, status, data_comanda, data_livrare, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                    (id_l, nume, tel, tl, nl, sod, cod, aod, sos, cos, aos, add, dp, rama, pr, pl, pr+pl, "Comandă Nouă", data_c.strftime("%d-%m-%Y"), data_l.strftime("%d-%m-%Y"), note_p))
                    conn.commit(); st.success("✅ Salvat!"); st.rerun()
                else: st.error(f"⚠️ Lipsesc: {', '.join(errs) if errs else 'Preț total'}")

# --- 3. TABEL PLĂȚI & FIȘE ---
elif choice == "📋 Tabel Plăți & Fișe":
    st.header("📋 Gestiune Clienți")
    search = st.text_input("🔍 Caută după nume:", "").strip().lower()
   
    df = pd.read_sql_query('''SELECT c.id, l.nume_locatie as Folder, c.nume as Pacient, c.status, c.total,
                              COALESCE((SELECT SUM(suma) FROM plati WHERE id_client = c.id), 0) as platit
                              FROM clienti c JOIN locatii l ON c.id_locatie = l.id''', conn)
    df['Rest'] = df['total'] - df['platit']
    df_f = df[df['Pacient'].str.lower().str.contains(search)] if search else df

    st.write("👇 **Click pe un rând pentru a deschide Fișa:**")
    styled_df = df_f.style.applymap(color_status, subset=['status']).format({'total': '{:,.2f}', 'platit': '{:,.2f}', 'Rest': '{:,.2f}'})

    event = st.dataframe(
        styled_df, use_container_width=True, on_select="rerun", selection_mode="single-row", hide_index=True
    )

    selected_rows = event.get("selection", {}).get("rows", [])
    if selected_rows:
        st.session_state['selected_client_id'] = int(df_f.iloc[selected_rows[0]]['id'])

    if st.session_state['selected_client_id']:
        id_p = st.session_state['selected_client_id']
        det = pd.read_sql_query(f"SELECT * FROM clienti WHERE id = {id_p}", conn).iloc[0]
        pl_ist = pd.read_sql_query(f"SELECT id, suma, data FROM plati WHERE id_client = {id_p}", conn)
       
        st.divider(); st.subheader(f"📑 FIȘA: {det['nume']}")
        f1, f2, f3 = st.columns([1.5, 1, 1])
        with f1:
            st.write(f"📞 {det['tel']} | 👓 {det['rama']} / {det['nume_lentila']}")
            st.write(f"👁️ OD: {det['sf_od'] or '-'}/{det['cl_od'] or '-'} | OS: {det['sf_os'] or '-'}/{det['cl_os'] or '-'}")
            if is_admin:
                n_nt = st.text_area("📝 Note (Se salvează la buton):", value=det['note'], key=f"nt_{id_p}")
                if st.button("Salvează Note"):
                    conn.execute("UPDATE clienti SET note=? WHERE id=?", (n_nt, id_p)); conn.commit(); st.rerun()
                
                # --- BUTON ȘTERGERE CLIENT (DOAR ADMIN) ---
                st.divider()
                with st.expander("🗑️ Zonă Periculoasă"):
                    confirm_del = st.checkbox("Confirm ștergerea definitivă a acestui client")
                    if st.button("Șterge Client Complet", type="secondary"):
                        if confirm_del:
                            conn.execute(f"DELETE FROM plati WHERE id_client = {id_p}")
                            conn.execute(f"DELETE FROM clienti WHERE id = {id_p}")
                            conn.commit()
                            st.session_state['selected_client_id'] = None
                            st.success("Client șters!")
                            st.rerun()
                        else:
                            st.warning("Bifează confirmarea pentru a șterge.")
            else: 
                st.info(f"Note: {det['note']}")
        with f2:
            st.metric("REST", f"{(det['total'] - pl_ist['suma'].sum()):,.2f} RON")
            if is_admin:
                r_n = st.number_input("Adaugă Rată:", min_value=0.0)
                if st.button("➕ Adaugă Plată"):
                    if r_n > 0:
                        conn.execute("INSERT INTO plati (id_client, suma, data) VALUES (?,?,?)", (id_p, r_n, datetime.now().strftime("%d-%m-%Y %H:%M")))
                        conn.commit(); st.rerun()
               
                # ACTUALIZARE AUTOMATĂ STATUS
                stati = ["Comandă Nouă", "Comandată", "Livrată + Rate", "Finalizată", "Problemă"]
                current_idx = stati.index(det['status']) if det['status'] in stati else 0
                n_s = st.selectbox("Status Comandă (Se salvează automat):", stati, index=current_idx, key=f"st_{id_p}")
               
                if n_s != det['status']:
                    conn.execute("UPDATE clienti SET status=? WHERE id=?", (n_s, id_p))
                    conn.commit()
                    st.rerun()
                   
        with f3:
            st.write("📜 Istoric:"); st.dataframe(pl_ist[['suma', 'data']], hide_index=True)
            if is_admin and not pl_ist.empty and st.button("🗑️ Șterge Ultima Plată"):
                conn.execute(f"DELETE FROM plati WHERE id = (SELECT MAX(id) FROM plati WHERE id_client = {id_p})"); conn.commit(); st.rerun()

# --- 4. ADMINISTRARE USERI ---
elif choice == "🛡️ Administrare Useri" and is_admin:
    st.header("🛡️ Gestiune Utilizatori")
    with st.form("u_n", clear_on_submit=True):
        c1, c2, c3 = st.columns(3); nu, np, nr = c1.text_input("User *"), c2.text_input("Parolă *"), c3.selectbox("Rol", ["User", "Admin"])
        if st.form_submit_button("Adaugă"):
            if nu and np:
                try:
                    conn.execute("INSERT INTO utilizatori (username, password, rol) VALUES (?,?,?)", (nu, np, nr))
                    conn.commit(); st.success("Creat!"); st.rerun()
                except: st.error("Existent!")
    st.table(pd.read_sql_query("SELECT id, username, rol FROM utilizatori", conn))
    d_id = st.number_input("ID de șters", min_value=2, step=1)
    if st.button("Elimină"): conn.execute(f"DELETE FROM utilizatori WHERE id = {d_id}"); conn.commit(); st.rerun()

conn.close()
