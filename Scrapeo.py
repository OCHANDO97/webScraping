from playwright.sync_api import sync_playwright
import numpy as np
import pandas as pd
import re
import os
os.environ["NODE_OPTIONS"] = "--max-old-space-size=4096"

class Scrapeo():

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.listLink = []
        self.arrayAcadesa = ['subCategoria', 'Categories', 'Marca', 'Name', 'Precio',
                            'Stock', 'Descripcion', 'images URL', 'EAN']

        self.todosAcadesa = np.empty([0, len(self.arrayAcadesa)])

    def run(self):
        with sync_playwright() as self.playwright:
            chromium = self.playwright.chromium
            self.browser = chromium.launch(headless=True)
            self.page = self.browser.new_page()
            self.page.goto("http://www.acadesa.com/productos/inicio.asp", timeout=0)

            listaCategoria = self._linkSubCategoriasAcadesa(self.page)
            for i in (listaCategoria):
                self.page.goto(i, timeout=0)

                # en estas variables, preguntamos si la pagina de la SubCategoria tiene 2 o mas paginas
                pageComplete = 0
                count_page_vista = self.page.query_selector_all(".paginacion-producto a")

                # las condiciones si la pagina tiene o no paginas
                if (len(count_page_vista) == 0):
                    self.page.wait_for_selector('.container-grid-products')
                    self._obtenerLinkProductoAcadesa(self.page)
                    self._obtenerDataAcadesaScraping(self.page)

                elif (len(count_page_vista) > 6):
                    pageComplete = len(count_page_vista) - 1
                else:
                    pageComplete = len(count_page_vista) + 1
                    paginaActual = self.page.evaluate('() => document.location.href')
                    for i in range(1, pageComplete):
                        self.page.goto(paginaActual, timeout=0)
                        # pasamos a la siguente pagina clikeando

                        self.page.locator(".paginacion-producto > a:nth-child("+str(i)+")").click()
                        self.page.wait_for_selector('.container-grid-products')

                        self._obtenerLinkProductoAcadesa(self.page)
                        self._obtenerDataAcadesaScraping(self.page)

            self.browser.close()

    def _linkSubCategoriasAcadesa(self, page):
        listaUrl = np.array([])
        categorias = page.query_selector_all('.acadesa-filtro-item')
        for item in categorias:
            subCategorias = item.query_selector_all('.acadesa-subfiltro li ')
            for i in subCategorias:
                # alamcenamos los link de las subcategorias
                listaUrl = np.append(listaUrl, i.eval_on_selector("a", "el => el.href"))
        return listaUrl


        # funcion para obeter los link de los productos
    def _obtenerLinkProductoAcadesa(self, page):

        page.wait_for_selector('.col-content')
        data = page.query_selector_all('.col-content')
        for item in data:
            link = item.eval_on_selector(".home-product-name a", "el => el.href")
            self.listLink.append(link)

        # Funcion que te obtiene los datos de cada articulo de la pagina de acadesa
    def _obtenerDataAcadesaScraping(self, page):

        for enlaces in self.listLink:
            listProductoActual = np.array([])
            paginaSubCategoria = page.evaluate('() => document.location.href')
            page.goto(paginaSubCategoria, timeout=0)
            data = page.query_selector('.banner-heading-home')
            if data is not None:
                dataSubCategoria = str(data.inner_text()).strip()
            else:
            # Manejar el caso en el que data es None
                dataSubCategoria = ""

            listProductoActual = np.append(listProductoActual, dataSubCategoria)
            page.goto(enlaces, timeout=0)

            # guardamos todos los datos de dichas paginas
            categoria = page.query_selector('.categoria')
            listProductoActual = np.append(listProductoActual, str(categoria.inner_text()).strip())

            page.wait_for_selector('.single-product-name')
            nameEtiqueta = page.query_selector('.single-product-name')
            precioEtiqueta = page.query_selector('.single-product-price')
            EANetiqueta = page.query_selector('.single-product-desc')

            # se pasa funcion strip() para quitar espacios
            nameCompleto = str(nameEtiqueta.inner_text()).strip()
            # para obtener las descripciones
            allDescripciones = page.query_selector_all('.single-product-contents')


            # marca
            # Para obtener la marca de acadesa ya q tiene simbolos raros
            esMarca = re.search(r'\((.*?)\)', nameCompleto)
            marcaOriginal = ""
            if esMarca:
                marcaOriginal = esMarca.group(1)
                if any(character.isnumeric() for character in marcaOriginal):
                    marcaOriginal = ""
                elif any(character.isspace() for character in marcaOriginal):
                    marcaOriginal = ""
                else:
                    marcaOriginal = esMarca.group(1)
            else:
                marcaOriginal = ""

            listProductoActual = np.append(listProductoActual, marcaOriginal)

            # nombre
            # elimina los () que encuentre en el nombre
            nameSinParentesis = re.sub("[()]", "", nameCompleto)
            listProductoActual = np.append(
                listProductoActual, nameSinParentesis)

            # precio
            precio = str(precioEtiqueta.inner_text()).strip()
            precio = precio[:-2]
            precio = precio.replace('.', '')
            precio = precio.replace(',', '.')
            listProductoActual = np.append(listProductoActual, float(precio))

            # stock
            stock = page.query_selector('.stockage')
            if(str(stock.inner_text()).strip() == 'En Stock'):
                listProductoActual = np.append(listProductoActual, 1)
            else:
                listProductoActual = np.append(listProductoActual, int(0))

            # descripcion
            for item in allDescripciones:
                descripcion = item.query_selector('.single-product-desc')
                listProductoActual = np.append(listProductoActual, str(descripcion.inner_text().strip()))
            # imagen
            listProductoActual = np.append(listProductoActual, page.eval_on_selector(".single-product-thumb-frame a img", "el => el.src"))

            # EAN
            listProductoActual = np.append(listProductoActual, str(EANetiqueta.inner_text().strip()))

            # aqui se almacena toda la informacion en la matriz,
            self.todosAcadesa = np.append(self.todosAcadesa, [listProductoActual], axis=0)

            contador=len(self.todosAcadesa)
            if contador % 1 == 0: # va escribiendo cada multiplo de 10
                print(f" \r   Se han scrapeado {contador} productos", end="")
            
            page.goto(paginaSubCategoria, timeout=0)
        # aqui borramos la lista de enlaces breviamente ya usado
        # self.listLink.clear()
        self.listLink = []

    def saveDataAcadesa(self, guardarAcadesa):  # guarda datos en el fichero Acadesa
        # se almacena los datos del scraping de acadesa

        dfSaveAcadesa = pd.DataFrame(self.todosAcadesa, columns=self.arrayAcadesa)
        # guardamos los datos a la ruta especificada y lo pasamos a excel
        dfSaveAcadesa.to_excel(guardarAcadesa, index=False)




acadesa = Scrapeo()
acadesa.run()
acadesa.saveDataAcadesa("acadesa.xlsx")
