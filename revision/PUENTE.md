# Montar el puente (una sola vez, ~10 minutos)

El puente es un Google Apps Script que recibe lo que Ana escribe en la web y lo guarda en `revision/` dentro de este repo.

## 1. Token de GitHub (solo para este repo)
1. https://github.com/settings/personal-access-tokens/new
2. Nombre: `revision-web` · Caducidad: 1 año.
3. Repository access → **Only select repositories** → `antonioomsg/ana-martinez`.
4. Permissions → Repository permissions → **Contents: Read and write**.
5. Generate token y copia el valor (`github_pat_…`).

## 2. Apps Script
1. https://script.google.com/home/projects/create (con la cuenta de la empresa).
2. Ponle de nombre `Revisión ana-martinez`.
3. Borra lo que haya en `Código.gs` y pega el contenido de [`puente/Code.gs`](puente/Code.gs).
4. ⚙️ Configuración del proyecto → **Propiedades del script** → añade:
   - `CLAVE` = la clave del enlace privado
   - `GITHUB_TOKEN` = el token del paso 1
   - `REPO` = `antonioomsg/ana-martinez`
   - `RAMA` = `main`
5. **Implementar → Nueva implementación** → tipo **Aplicación web** → Ejecutar como **Yo** · Acceso **Cualquier usuario** → Implementar → autoriza los permisos.
6. Copia la **URL de la aplicación web** (`https://script.google.com/macros/s/…/exec`).

## 3. Conectar la web
Pega esa URL en `ENDPOINT` al principio de `assets/revision.js`, regenera (`python3 scripts/build.py .`) y publica.

## Enlace para Ana
`https://<dominio-de-la-web>/?revisar=CLAVE`

Lo abre una vez en su móvil y queda activado en ese navegador. Para desactivarlo: `?revisar=salir`.

Si la clave se filtra, cámbiala en las Propiedades del script y envía a Ana el enlace nuevo.
