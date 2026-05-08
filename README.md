# Sistema de Inventario en Streamlit

Archivos necesarios para subir a GitHub:

- `app.py`
- `requirements.txt`

## Cómo correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Cómo subir a Streamlit Community Cloud

1. Crear un repositorio en GitHub.
2. Subir `app.py` y `requirements.txt`.
3. Entrar a Streamlit Community Cloud.
4. Elegir el repositorio.
5. En **Main file path**, escribir: `app.py`.
6. Presionar **Deploy**.

## Importante

La app guarda datos en `inventario.json`. En Streamlit Cloud este archivo puede reiniciarse cuando la app se actualiza o redeploya, por eso se recomienda descargar respaldo en Excel, CSV o JSON.
