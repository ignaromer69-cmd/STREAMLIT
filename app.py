import json
from pathlib import Path
from io import BytesIO, StringIO

import pandas as pd
import streamlit as st

# ---------------- CONFIGURACIÓN GENERAL ---------------- #
st.set_page_config(
    page_title="Sistema de Inventario",
    page_icon="📦",
    layout="wide"
)

DB_PATH = Path(__file__).parent / "inventario.json"

COLUMNAS = [
    "ID",
    "Número Serie",
    "SAP",
    "SOLOT",
    "Documento Material",
    "Nombre Usuario",
    "Almacén",
    "Sociedad",
    "Centro",
    "Material",
    "Orden Compra",
    "Stock",
    "Stock Original",
]

CAMPOS_FORM = {
    "serie": "Número Serie",
    "sap": "SAP",
    "solot": "SOLOT",
    "documento": "Documento Material",
    "usuario": "Nombre Usuario",
    "almacen": "Almacén",
    "sociedad": "Sociedad",
    "centro": "Centro",
    "nombre": "Material",
    "orden": "Orden Compra",
    "cantidad": "Stock",
    "cantidad_original": "Stock Original",
}


def cargar_datos():
    """Carga la base local inventario.json. En Streamlit Cloud se mantiene mientras exista el archivo."""
    if DB_PATH.exists():
        try:
            with open(DB_PATH, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            inventario = {int(k): v for k, v in datos.get("inventario", {}).items()}
            contador_id = int(datos.get("contador_id", 1))
            for item in inventario.values():
                item.setdefault("cantidad_original", item.get("cantidad", 0))
            return inventario, contador_id
        except Exception:
            return {}, 1
    return {}, 1


def guardar_datos():
    datos = {
        "inventario": st.session_state.inventario,
        "contador_id": st.session_state.contador_id,
    }
    with open(DB_PATH, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)


def inicializar_estado():
    if "inventario" not in st.session_state:
        inventario, contador_id = cargar_datos()
        st.session_state.inventario = inventario
        st.session_state.contador_id = contador_id
    if "editar_id" not in st.session_state:
        st.session_state.editar_id = None


def inventario_a_dataframe():
    filas = []
    for key, datos in st.session_state.inventario.items():
        filas.append({
            "ID": key,
            "Número Serie": datos.get("serie", ""),
            "SAP": datos.get("sap", ""),
            "SOLOT": datos.get("solot", ""),
            "Documento Material": datos.get("documento", ""),
            "Nombre Usuario": datos.get("usuario", ""),
            "Almacén": datos.get("almacen", ""),
            "Sociedad": datos.get("sociedad", ""),
            "Centro": datos.get("centro", ""),
            "Material": datos.get("nombre", ""),
            "Orden Compra": datos.get("orden", ""),
            "Stock": int(datos.get("cantidad", 0)),
            "Stock Original": int(datos.get("cantidad_original", datos.get("cantidad", 0))),
        })
    return pd.DataFrame(filas, columns=COLUMNAS)


def validar_numero(valor, nombre="cantidad"):
    try:
        numero = int(valor)
        if numero < 0:
            st.error(f"La {nombre} no puede ser negativa.")
            return None
        return numero
    except Exception:
        st.error(f"La {nombre} debe ser numérica.")
        return None


def limpiar_formulario():
    for key in ["serie", "sap", "solot", "documento", "usuario", "almacen", "sociedad", "centro", "nombre", "orden", "cantidad"]:
        st.session_state[f"form_{key}"] = ""
    st.session_state.editar_id = None


def agregar_o_modificar_material(valores):
    cantidad = validar_numero(valores["cantidad"], "cantidad")
    if cantidad is None:
        return

    faltantes = [campo for campo, valor in valores.items() if campo != "cantidad" and not str(valor).strip()]
    if faltantes:
        st.warning("Complete todos los campos antes de guardar.")
        return

    item = {
        "serie": valores["serie"].strip(),
        "sap": valores["sap"].strip(),
        "solot": valores["solot"].strip(),
        "documento": valores["documento"].strip(),
        "usuario": valores["usuario"].strip(),
        "almacen": valores["almacen"].strip(),
        "sociedad": valores["sociedad"].strip(),
        "centro": valores["centro"].strip(),
        "nombre": valores["nombre"].strip(),
        "orden": valores["orden"].strip(),
        "cantidad": cantidad,
    }

    if st.session_state.editar_id is not None:
        item_id = st.session_state.editar_id
        stock_original_anterior = int(st.session_state.inventario.get(item_id, {}).get("cantidad_original", cantidad))
        item["cantidad_original"] = max(cantidad, stock_original_anterior)
        st.session_state.inventario[item_id] = item
        st.success("Material modificado correctamente.")
    else:
        item_id = st.session_state.contador_id
        item["cantidad_original"] = cantidad
        st.session_state.inventario[item_id] = item
        st.session_state.contador_id += 1
        st.success("Material agregado correctamente.")

    guardar_datos()
    limpiar_formulario()


def eliminar_material(item_id):
    if item_id in st.session_state.inventario:
        del st.session_state.inventario[item_id]
        guardar_datos()
        st.success("Material eliminado correctamente.")
    else:
        st.error("No se encontró el material seleccionado.")


def rebajar_por_serie(serie, cantidad_rebaja):
    if not serie.strip():
        st.warning("Ingrese el número de serie.")
        return
    cantidad = validar_numero(cantidad_rebaja, "cantidad a rebajar")
    if cantidad is None or cantidad <= 0:
        st.warning("La cantidad a rebajar debe ser mayor a 0.")
        return

    encontrado = None
    for key, datos in st.session_state.inventario.items():
        if str(datos.get("serie", "")).strip().lower() == serie.strip().lower():
            encontrado = key
            break

    if encontrado is None:
        st.error("Material no encontrado.")
        return

    stock_actual = int(st.session_state.inventario[encontrado].get("cantidad", 0))
    if cantidad > stock_actual:
        st.warning(f"No hay suficiente stock. Disponible actual: {stock_actual}")
        return

    st.session_state.inventario[encontrado]["cantidad"] = stock_actual - cantidad
    guardar_datos()
    st.success(f"Rebaja realizada. Cantidad rebajada: {cantidad} | Disponible: {stock_actual - cantidad}")


def rebajar_por_sap(sap, cantidad_rebaja):
    if not sap.strip():
        st.warning("Ingrese el SAP.")
        return
    cantidad = validar_numero(cantidad_rebaja, "cantidad a rebajar")
    if cantidad is None or cantidad <= 0:
        st.warning("La cantidad a rebajar debe ser mayor a 0.")
        return

    sap_limpio = sap.strip().lower()
    ids_sap = []
    stock_total = 0
    for key, datos in st.session_state.inventario.items():
        if str(datos.get("sap", "")).strip().lower() == sap_limpio:
            stock = int(datos.get("cantidad", 0))
            if stock > 0:
                ids_sap.append(key)
                stock_total += stock

    if not ids_sap:
        st.error("No se encontró stock disponible para ese SAP.")
        return
    if cantidad > stock_total:
        st.warning(f"No hay suficiente stock para ese SAP. Disponible actual: {stock_total}")
        return

    pendiente = cantidad
    for key in ids_sap:
        if pendiente == 0:
            break
        stock = int(st.session_state.inventario[key].get("cantidad", 0))
        rebaja_item = min(stock, pendiente)
        st.session_state.inventario[key]["cantidad"] = stock - rebaja_item
        pendiente -= rebaja_item

    guardar_datos()
    resumen = resumen_sap(sap)
    st.success(
        f"SAP {sap.upper()} rebajado correctamente. Rebaja realizada: {cantidad}. "
        f"Total rebajado/consumido: {resumen['rebajado']}. Disponible actual: {resumen['disponible']}."
    )


def resumen_sap(sap):
    sap_limpio = sap.strip().lower()
    total_original = 0
    total_disponible = 0
    filas = []
    for key, datos in st.session_state.inventario.items():
        if str(datos.get("sap", "")).strip().lower() == sap_limpio:
            original = int(datos.get("cantidad_original", datos.get("cantidad", 0)))
            disponible = int(datos.get("cantidad", 0))
            rebajado = original - disponible
            total_original += original
            total_disponible += disponible
            filas.append({
                "ID": key,
                "Serie": datos.get("serie", ""),
                "Material": datos.get("nombre", ""),
                "Total": original,
                "Rebajado": rebajado,
                "Disponible": disponible,
            })
    return {
        "total": total_original,
        "rebajado": total_original - total_disponible,
        "disponible": total_disponible,
        "filas": pd.DataFrame(filas),
    }


def importar_archivo(archivo):
    if archivo is None:
        return
    try:
        nombre = archivo.name.lower()
        if nombre.endswith(".csv"):
            df = pd.read_csv(archivo, sep=None, engine="python", encoding="utf-8-sig")
        else:
            df = pd.read_excel(archivo)

        columnas_requeridas = ["Número Serie", "SAP", "SOLOT", "Documento Material", "Nombre Usuario", "Almacén", "Sociedad", "Centro", "Material", "Orden Compra", "Stock"]
        faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if faltantes:
            st.error("El archivo no tiene todas las columnas necesarias: " + ", ".join(faltantes))
            return

        for _, fila in df.iterrows():
            stock = int(fila.get("Stock", 0) or 0)
            st.session_state.inventario[st.session_state.contador_id] = {
                "serie": str(fila.get("Número Serie", "")),
                "sap": str(fila.get("SAP", "")),
                "solot": str(fila.get("SOLOT", "")),
                "documento": str(fila.get("Documento Material", "")),
                "usuario": str(fila.get("Nombre Usuario", "")),
                "almacen": str(fila.get("Almacén", "")),
                "sociedad": str(fila.get("Sociedad", "")),
                "centro": str(fila.get("Centro", "")),
                "nombre": str(fila.get("Material", "")),
                "orden": str(fila.get("Orden Compra", "")),
                "cantidad": stock,
                "cantidad_original": stock,
            }
            st.session_state.contador_id += 1
        guardar_datos()
        st.success("Base de datos importada correctamente.")
    except Exception as error:
        st.error(f"No se pudo importar el archivo: {error}")


def generar_excel(df):
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventario")
        ws = writer.book["Inventario"]
        for col in ws.columns:
            max_len = max(len(str(cell.value)) if cell.value is not None else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 35)
    salida.seek(0)
    return salida


def generar_csv(df):
    return df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")


# ---------------- INTERFAZ STREAMLIT ---------------- #
inicializar_estado()

st.title("📦 Sistema de Inventario de Materiales")
st.caption("Versión adaptada para Streamlit Online y carga por GitHub")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem;}
[data-testid="stMetricValue"] {font-size: 1.7rem;}
</style>
""", unsafe_allow_html=True)

df_actual = inventario_a_dataframe()
stock_total = int(df_actual["Stock Original"].sum()) if not df_actual.empty else 0
stock_disponible = int(df_actual["Stock"].sum()) if not df_actual.empty else 0
stock_rebajado = stock_total - stock_disponible

col1, col2, col3, col4 = st.columns(4)
col1.metric("Materiales registrados", len(df_actual))
col2.metric("Stock total", stock_total)
col3.metric("Stock rebajado", stock_rebajado)
col4.metric("Stock disponible", stock_disponible)

pestana_agregar, pestana_rebajar, pestana_buscar, pestana_tabla, pestana_importar = st.tabs([
    "➕ Agregar / Modificar",
    "📉 Rebajar Stock",
    "🔎 Buscar SAP",
    "📋 Inventario",
    "📁 Importar / Exportar",
])

with pestana_agregar:
    st.subheader("Agregar o modificar material")

    if st.session_state.editar_id is not None:
        st.info(f"Editando material ID {st.session_state.editar_id}. Cambie los campos y presione Guardar.")

    with st.form("form_material"):
        c1, c2, c3 = st.columns(3)
        valores = {}
        with c1:
            valores["serie"] = st.text_input("Número Serie", key="form_serie")
            valores["solot"] = st.text_input("SOLOT", key="form_solot")
            valores["usuario"] = st.text_input("Nombre Usuario", key="form_usuario")
            valores["sociedad"] = st.text_input("Sociedad", key="form_sociedad")
        with c2:
            valores["sap"] = st.text_input("SAP", key="form_sap")
            valores["documento"] = st.text_input("Documento Material", key="form_documento")
            valores["almacen"] = st.text_input("Almacén", key="form_almacen")
            valores["centro"] = st.text_input("Centro", key="form_centro")
        with c3:
            valores["nombre"] = st.text_input("Nombre Material", key="form_nombre")
            valores["orden"] = st.text_input("Orden Compra", key="form_orden")
            valores["cantidad"] = st.text_input("Cantidad", key="form_cantidad")

        guardar = st.form_submit_button("Guardar material", use_container_width=True)
        if guardar:
            agregar_o_modificar_material(valores)
            st.rerun()

    st.divider()
    st.write("Seleccione un ID para cargarlo en el formulario o eliminarlo.")
    if not df_actual.empty:
        id_seleccionado = st.selectbox("ID del material", df_actual["ID"].tolist())
        col_editar, col_eliminar, col_cancelar = st.columns(3)
        if col_editar.button("Cargar para modificar", use_container_width=True):
            item = st.session_state.inventario[int(id_seleccionado)]
            st.session_state.editar_id = int(id_seleccionado)
            st.session_state.form_serie = item.get("serie", "")
            st.session_state.form_sap = item.get("sap", "")
            st.session_state.form_solot = item.get("solot", "")
            st.session_state.form_documento = item.get("documento", "")
            st.session_state.form_usuario = item.get("usuario", "")
            st.session_state.form_almacen = item.get("almacen", "")
            st.session_state.form_sociedad = item.get("sociedad", "")
            st.session_state.form_centro = item.get("centro", "")
            st.session_state.form_nombre = item.get("nombre", "")
            st.session_state.form_orden = item.get("orden", "")
            st.session_state.form_cantidad = str(item.get("cantidad", 0))
            st.rerun()
        if col_eliminar.button("Eliminar material", use_container_width=True):
            eliminar_material(int(id_seleccionado))
            st.rerun()
        if col_cancelar.button("Cancelar edición", use_container_width=True):
            limpiar_formulario()
            st.rerun()
    else:
        st.info("Aún no hay materiales ingresados.")

with pestana_rebajar:
    st.subheader("Rebajar stock")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Rebaja por número de serie**")
        serie_rebaja = st.text_input("Número Serie", key="serie_rebaja")
        cantidad_rebaja = st.number_input("Cantidad a rebajar", min_value=1, step=1, key="cantidad_rebaja")
        if st.button("Rebajar por Serie", use_container_width=True):
            rebajar_por_serie(serie_rebaja, cantidad_rebaja)
            st.rerun()
    with c2:
        st.markdown("**Rebaja directa por SAP**")
        sap_rebaja = st.text_input("SAP", key="sap_rebaja")
        cantidad_rebaja_sap = st.number_input("Cantidad a rebajar por SAP", min_value=1, step=1, key="cantidad_rebaja_sap")
        if st.button("Rebajar por SAP", use_container_width=True):
            rebajar_por_sap(sap_rebaja, cantidad_rebaja_sap)
            st.rerun()

with pestana_buscar:
    st.subheader("Buscar información por SAP")
    sap_busqueda = st.text_input("Ingrese SAP para revisar total, rebajado y disponible")
    if st.button("Buscar SAP", use_container_width=True):
        if not sap_busqueda.strip():
            st.warning("Ingrese un SAP para buscar.")
        else:
            resultado = resumen_sap(sap_busqueda)
            if resultado["filas"].empty:
                st.error("No se encontraron materiales con ese SAP.")
            else:
                a, b, c = st.columns(3)
                a.metric("Cantidad total", resultado["total"])
                b.metric("Cantidad rebajada / consumida", resultado["rebajado"])
                c.metric("Cantidad disponible", resultado["disponible"])
                st.dataframe(resultado["filas"], use_container_width=True, hide_index=True)

with pestana_tabla:
    st.subheader("Base de datos del inventario")
    if df_actual.empty:
        st.info("No hay datos para mostrar.")
    else:
        busqueda = st.text_input("Filtro rápido por serie, SAP, material, usuario u orden")
        df_filtrado = df_actual.copy()
        if busqueda:
            texto = busqueda.lower()
            df_filtrado = df_filtrado[df_filtrado.astype(str).apply(lambda row: row.str.lower().str.contains(texto).any(), axis=1)]
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

with pestana_importar:
    st.subheader("Importar y exportar base de datos")
    archivo = st.file_uploader("Importar CSV o Excel", type=["csv", "xlsx"])
    if st.button("Importar archivo", use_container_width=True):
        importar_archivo(archivo)
        st.rerun()

    st.divider()
    if df_actual.empty:
        st.info("No hay datos para exportar.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "Descargar Excel",
            data=generar_excel(df_actual),
            file_name="base_datos_inventario.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        c2.download_button(
            "Descargar CSV",
            data=generar_csv(df_actual),
            file_name="base_datos_inventario.csv",
            mime="text/csv",
            use_container_width=True,
        )
        c3.download_button(
            "Descargar inventario.json",
            data=json.dumps({"inventario": st.session_state.inventario, "contador_id": st.session_state.contador_id}, indent=4, ensure_ascii=False),
            file_name="inventario.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()
    st.warning("En Streamlit Cloud los archivos guardados pueden reiniciarse si la app se redeploya. Para respaldo, descargue el Excel/CSV o inventario.json periódicamente.")
