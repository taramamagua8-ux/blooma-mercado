// ======================================================================
// ARCHIVO: index.js
// DESCRIPCIÓN: Este archivo contiene toda la lógica de la página principal
//              (index.html) del mercado "Melchor Ocampo". Maneja la interacción
//              con el usuario, el carrito de compras, los favoritos, los
//              locales, la búsqueda, el reproductor de audio y más.
// ======================================================================

// ======================================================================
// 1. VARIABLES GLOBALES
//    Son variables que se pueden usar desde cualquier parte del código.
//    Algunas vienen definidas en el archivo HTML (usuarioLogueado,
//    urlCarrito, urlAudio) y otras se declaran aquí.
// ======================================================================

// Estas variables están definidas en el HTML (mediante etiquetas <script>)
// y contienen información del usuario, la URL del carrito y la URL del audio.
// usuarioLogueado → true/false si hay una sesión activa.
// urlCarrito → la dirección a la que ir cuando se hace clic en el carrito.
// urlAudio → la ruta del archivo de música de fondo.

// Variable que guardará el producto que el usuario está viendo en el modal
// (ventana emergente) de producto. Inicialmente está vacía (null).
let currentProducto = null;

// Variable que almacena la cantidad de unidades disponibles (stock) del producto
// actual que se muestra en el modal.
let currentStock = 0;

// ======================================================================
// 2. MAPA DE LOCALES
//    Un objeto donde la clave es el código del local (ej. "LOC-COM-01")
//    y el valor es otro objeto con el nombre y la categoría del local.
// ======================================================================

let localesMap = {};

// ======================================================================
// 3. FUNCIÓN PARA CARGAR LOCALES DESDE LA API
//    Esta función se comunica con el servidor para obtener la lista de
//    todos los locales y guardarlos en el mapa localesMap.
// ======================================================================

async function cargarLocales() {
    // "async" indica que esta función es asíncrona, es decir, puede esperar
    // respuestas del servidor sin bloquear el resto de la página.

    try {
        // Intenta hacer una petición GET a la dirección '/api/locales'
        // fetch() devuelve una promesa que resuelve en la respuesta del servidor.
        const res = await fetch('/api/locales');

        // Si la respuesta no es correcta (código diferente de 200), lanza un error.
        if (!res.ok) throw new Error('Error al cargar locales');

        // Convierte la respuesta (que viene en formato JSON) a un objeto JavaScript.
        const data = await res.json();

        // Recorre cada elemento (local) de la lista recibida.
        data.forEach(l => {
            // Para cada local, guarda en el mapa localesMap su código como clave,
            // y como valor un objeto con su nombre y categoría.
            localesMap[l.codigo] = { nombre: l.nombre, categoria: l.categoria };
        });

        // Muestra en la consola del navegador (para desarrolladores) cuántos locales se cargaron.
        console.log('✅ Locales cargados:', Object.keys(localesMap).length);

    } catch (e) {
        // Si ocurre algún error (problema de red, servidor caído, etc.),
        // se muestra un mensaje de error en la consola.
        console.error('❌ Error cargando locales:', e);
        // No se hace nada más, la página seguirá funcionando pero algunos
        // locales podrían mostrarse solo con su código en lugar de su nombre.
    }
}

// ======================================================================
// 4. FUNCIÓN PARA MOSTRAR NOTIFICACIONES ("TOAST")
//    Muestra un mensaje emergente en la parte inferior de la pantalla
//    durante unos segundos.
// ======================================================================

function showToast(msg, isError = false) {
    // Obtiene el elemento HTML con id "toastMsg" (debe existir en la página).
    const toast = document.getElementById('toastMsg');

    // Asigna el mensaje recibido como texto dentro de ese elemento.
    toast.textContent = msg;

    // Cambia el color de fondo según si es un error (rojo) o un éxito (verde).
    toast.style.background = isError ? '#e74c3c' : '#2ecc71';

    // Agrega la clase "show" para que el toast se haga visible (con animación).
    toast.classList.add('show');

    // Después de 3 segundos (3000 milisegundos), quita la clase "show"
    // para que desaparezca.
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// ======================================================================
// 5. FUNCIONES PARA EL MODAL DE PRODUCTO
//    El modal es una ventana emergente que muestra los detalles de un
//    producto y permite agregarlo al carrito o a favoritos.
// ======================================================================

// Función que abre el modal de producto, recibiendo un objeto "producto"
// con sus propiedades (id, nombre, precio, stock).
function abrirModalProducto(producto) {
    // Primero verifica si el usuario está logueado.
    // Si no lo está, muestra un mensaje de error y redirige al login.
    if (!usuarioLogueado) {
        showToast('Debes iniciar sesión para agregar productos o favoritos', true);
        // Redirige a la página de login después de 1.5 segundos.
        setTimeout(() => window.location.href = '/login', 1500);
        return; // Sale de la función para no continuar.
    }

    // Guarda el producto actual en la variable global para usarlo después.
    currentProducto = producto;

    // Guarda el stock disponible en la variable global.
    currentStock = producto.stock;

    // Rellena los elementos del modal con la información del producto.
    document.getElementById('modalProductoNombre').innerText = producto.nombre;
    document.getElementById('modalProductoPrecio').innerText = producto.precio.toFixed(2);
    // toFixed(2) asegura que el precio tenga dos decimales (ej. 5.00).

    // Establece la cantidad inicial en 1.
    document.getElementById('modalCantidad').value = 1;

    // Agrega la clase "active" al modal para hacerlo visible (con animación).
    document.getElementById('productModal').classList.add('active');
}

// Función que cierra el modal y limpia el producto actual.
function cerrarModalProducto() {
    document.getElementById('productModal').classList.remove('active');
    currentProducto = null; // Olvida el producto seleccionado.
}

// Función asíncrona para agregar un producto al carrito.
// Recibe el ID del producto y la cantidad.
async function agregarAlCarrito(productoId, cantidad) {
    try {
        // Hace una petición POST al servidor en '/api/carrito/agregar'.
        const res = await fetch('/api/carrito/agregar', {
            method: 'POST', // Indica que enviamos datos.
            headers: { 'Content-Type': 'application/json' }, // Indicamos que enviamos JSON.
            body: JSON.stringify({ id: productoId, cantidad: cantidad }) // Convierte los datos a JSON.
        });

        // Espera la respuesta y la convierte a objeto JavaScript.
        const data = await res.json();

        // Si el servidor responde con éxito (data.success = true).
        if (data.success) {
            showToast(`✅ ${cantidad} unidad(es) agregada(s) al carrito`);
            // Actualiza el contador del carrito en la interfaz.
            actualizarContadorCarrito();
            // Cierra el modal.
            cerrarModalProducto();
        } else if (data.error === 'login requerido') {
            // Si el servidor dice que se requiere login, redirige al login.
            window.location.href = '/login';
        } else {
            // En caso de otro error, lo muestra en el toast.
            showToast(data.error || 'Error al agregar', true);
        }
    } catch(e) {
        // Si hay un error de red o conexión, muestra un mensaje genérico.
        showToast('Error de conexión', true);
    }
}

// Función asíncrona para agregar un producto a favoritos.
async function agregarAFavoritos(productoId) {
    try {
        const res = await fetch('/api/favoritos/agregar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ producto_id: productoId })
        });
        const data = await res.json();

        if (data.success) {
            showToast('❤️ Producto guardado en favoritos');
            cerrarModalProducto();
        } else if (data.error === 'Ya existe') {
            // Si el producto ya estaba en favoritos, lo notifica sin error.
            showToast('Este producto ya está en tus favoritos', false);
        } else if (data.error === 'login') {
            window.location.href = '/login';
        } else {
            showToast(data.error || 'Error al guardar', true);
        }
    } catch(e) {
        showToast('Error de conexión', true);
    }
}

// ======================================================================
// 6. EVENTOS DEL MODAL DE PRODUCTO
//    Asigna comportamientos a los botones y controles dentro del modal.
// ======================================================================

// Al hacer clic en el botón de cerrar (la "X") se cierra el modal.
document.getElementById('modalCerrar').addEventListener('click', cerrarModalProducto);

// Al hacer clic en "Agregar al carrito" dentro del modal.
document.getElementById('modalAgregarCarrito').addEventListener('click', () => {
    // Si no hay producto seleccionado, no hace nada.
    if (!currentProducto) return;

    // Obtiene la cantidad ingresada en el campo de cantidad.
    let cantidad = parseInt(document.getElementById('modalCantidad').value);
    // Si no es un número válido o es menor a 1, la ajusta a 1.
    if (isNaN(cantidad) || cantidad < 1) cantidad = 1;

    // Si la cantidad supera el stock disponible, muestra un mensaje y no agrega.
    if (cantidad > currentStock) {
        showToast(`Solo hay ${currentStock} disponibles`, true);
        return;
    }

    // Llama a la función para agregar al carrito.
    agregarAlCarrito(currentProducto.id, cantidad);
});

// Al hacer clic en "Agregar a favoritos".
document.getElementById('modalAgregarFavorito').addEventListener('click', () => {
    if (!currentProducto) return;
    agregarAFavoritos(currentProducto.id);
});

// Botón para disminuir la cantidad (restar 1).
document.getElementById('decrementQty').addEventListener('click', () => {
    let qty = parseInt(document.getElementById('modalCantidad').value);
    if (qty > 1) document.getElementById('modalCantidad').value = qty - 1;
});

// Botón para aumentar la cantidad (sumar 1), respetando el stock.
document.getElementById('incrementQty').addEventListener('click', () => {
    let qty = parseInt(document.getElementById('modalCantidad').value);
    if (qty < currentStock) {
        document.getElementById('modalCantidad').value = qty + 1;
    } else {
        showToast(`Máximo ${currentStock} unidades`, false);
    }
});

// Cuando el usuario cambia manualmente el valor del campo de cantidad.
document.getElementById('modalCantidad').addEventListener('change', function() {
    let val = parseInt(this.value);
    // Si no es número o menor a 1, lo fija a 1.
    if (isNaN(val) || val < 1) this.value = 1;
    // Si supera el stock, lo ajusta al stock y avisa.
    if (val > currentStock) {
        this.value = currentStock;
        showToast(`Stock máximo: ${currentStock}`, false);
    }
});

// Cerrar el modal si el usuario hace clic en el fondo oscuro (fuera del modal).
window.addEventListener('click', (e) => {
    const modal = document.getElementById('productModal');
    // Si el elemento clicado es exactamente el fondo (no un hijo), cierra.
    if (e.target === modal) cerrarModalProducto();
});

// ======================================================================
// 7. LÓGICA DE PRODUCTOS EN LA PÁGINA PRINCIPAL
//    Carga y muestra los productos en las secciones de "descuento" y "popular".
//    También maneja los filtros y la búsqueda.
// ======================================================================

// Variables que guardan el filtro activo (por defecto "all" = todos) y el término de búsqueda.
let activeSubNav = "all";
let activeSearchTerm = "";

// Función asíncrona que obtiene los productos del servidor y los muestra en pantalla.
async function cargarProductos() {
    try {
        // Pide la lista de productos al servidor.
        const response = await fetch('/api/productos');
        const productos = await response.json();

        // Obtiene los contenedores donde se pintarán los productos.
        const gridDiscount = document.getElementById('discountGrid');
        const gridPopular = document.getElementById('popularGrid');

        // Si no existen estos contenedores en la página, sale de la función.
        if (!gridDiscount || !gridPopular) return;

        // Copia la lista de productos en una variable "filtered" para aplicar filtros.
        let filtered = [...productos];

        // Si hay un filtro activo (diferente de "all"), se filtraría aquí.
        // En este código, no se usa activeSubNav para filtrar realmente,
        // pero se deja la estructura para futuras implementaciones.
        // (Actualmente solo filtra por búsqueda.)
        if (activeSubNav !== "all") {
            // (Comentario: aquí iría la lógica de filtro por categoría)
        }

        // Si hay un término de búsqueda, filtra los productos cuyo nombre lo contenga.
        if (activeSearchTerm) {
            filtered = filtered.filter(p => p.nombre.toLowerCase().includes(activeSearchTerm.toLowerCase()));
        }

        // Toma los primeros 8 productos para la sección "con descuento".
        const conDescuento = filtered.slice(0, 8);
        // Toma los siguientes 8 para la sección "populares".
        const populares = filtered.slice(8, 16);

        // Función interna que renderiza (pinta) los productos en un contenedor.
        function renderizar(container, productosArray) {
            // Si no hay productos, muestra un mensaje de "no hay productos".
            if (!productosArray.length) {
                container.innerHTML = '<div style="text-align:center; font-family: var(--font-sans); color: var(--text-mist); grid-column: 1/-1; padding: 2rem;">No hay productos disponibles bajo este filtro.</div>';
                return;
            }

            // Genera el HTML para cada producto y lo une en un solo string.
            container.innerHTML = productosArray.map(p => `
                <div class="product-card" data-id="${p.id}" data-nombre="${escapeHtml(p.nombre)}" data-precio="${p.precio}" data-stock="100">
                    <div class="badge-descuento">📦 Envío a local</div>
                    <div class="product-img">🍓</div>
                    <div class="product-info">
                        <h3>${escapeHtml(p.nombre)}</h3>
                        <div class="price-tag">$${p.precio}</div>
                        <button class="btn-add" data-id="${p.id}">AGREGAR AL CARRITO</button>
                    </div>
                </div>
            `).join('');

            // Ahora, para cada botón "AGREGAR AL CARRITO" dentro del contenedor,
            // le asignamos un evento de clic que abrirá el modal con el producto.
            container.querySelectorAll('.btn-add').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation(); // Evita que el clic se propague a otros elementos.

                    // Obtiene la tarjeta (card) del producto y sus datos.
                    const card = btn.closest('.product-card');
                    const id = parseInt(card.dataset.id);
                    const nombre = card.dataset.nombre;
                    const precio = parseFloat(card.dataset.precio);

                    // Para obtener el stock real, hacemos una petición específica al servidor.
                    // Si falla, usamos 100 como valor por defecto.
                    let stock = 100;
                    try {
                        const stockRes = await fetch(`/api/producto-stock/${id}`);
                        if (stockRes.ok) {
                            const stockData = await stockRes.json();
                            stock = stockData.stock;
                        }
                    } catch(e) {
                        console.warn(e);
                    }

                    // Abre el modal con los datos del producto.
                    abrirModalProducto({ id, nombre, precio, stock });
                });
            });
        }

        // Pinta los productos en sus respectivos contenedores.
        renderizar(gridDiscount, conDescuento);
        renderizar(gridPopular, populares);

    } catch(e) {
        // Si ocurre un error, lo muestra en la consola.
        console.error(e);
    }
}

// Función que se ejecuta al presionar el botón de búsqueda.
// Toma el texto del campo de búsqueda y redirige a la misma página con el parámetro "buscar".
function buscarProductos() {
    const query = document.getElementById("headerSearchInput").value;
    if (query.trim() !== "") {
        window.location.href = "/?buscar=" + encodeURIComponent(query);
    }
}

// ======================================================================
// 8. ACTUALIZAR CONTADOR DEL CARRITO
//    Pide al servidor los items del carrito y suma las cantidades para
//    mostrar el total en el ícono del carrito.
// ======================================================================

async function actualizarContadorCarrito() {
    // Si el usuario no está logueado, no hace nada.
    if (!usuarioLogueado) return;

    try {
        const res = await fetch('/api/carrito');
        const data = await res.json();

        let total = 0;
        if (data.items) {
            // Suma la cantidad de cada item.
            total = data.items.reduce((acc, i) => acc + i.cantidad, 0);
        }

        // Actualiza el elemento que muestra el número en el carrito.
        document.getElementById('cart-count').innerText = total;
    } catch(e) {
        // Si hay error, simplemente no actualiza.
    }
}

// ======================================================================
// 9. LÓGICA DE LOCALES (MODAL DE LOCALES)
//    Maneja la ventana emergente que muestra los locales de una categoría.
// ======================================================================

// Mapeo de categorías a listas de códigos de locales.
const localesPorCategoria = {
    'comida': ['LOC-COM-01', 'LOC-COM-02'],
    'cosmeticos': ['LOC-BEY-01', 'LOC-BEY-02'],
    'mascotas': ['LOC-MAS-01'],
    'dulceria': ['LOC-DUL-01']
};

// Lista completa de todos los códigos de locales (para búsqueda).
const todosLosLocales = ['LOC-COM-01', 'LOC-COM-02', 'LOC-BEY-01', 'LOC-BEY-02', 'LOC-MAS-01', 'LOC-DUL-01'];

// Referencias a elementos del modal de locales.
const modalOverlay = document.getElementById('modalLocales');
const modalTitulo = document.getElementById('modal-categoria-titulo');
const listaLocalesDiv = document.getElementById('lista-locales-modal');
const cerrarModalBtn = document.getElementById('cerrar-modal-btn');

// Función que abre el modal de locales para una categoría dada.
function abrirModal(categoria) {
    // Obtiene los códigos de locales para esa categoría.
    const codigos = localesPorCategoria[categoria];
    if (!codigos || codigos.length === 0) return;

    // Determina el título a mostrar según la categoría.
    let tituloMostrar = '';
    if (categoria === 'comida') tituloMostrar = '🍽️ COMIDA';
    else if (categoria === 'cosmeticos') tituloMostrar = '💄 COSMÉTICOS Y BELLEZA';
    else if (categoria === 'mascotas') tituloMostrar = '🐾 MASCOTAS';
    else if (categoria === 'dulceria') tituloMostrar = '🍬 DULCERÍA';
    modalTitulo.textContent = tituloMostrar;

    // Limpia la lista de locales.
    listaLocalesDiv.innerHTML = '';

    // Para cada código, crea un enlace (botón) con el nombre del local.
    codigos.forEach(cod => {
        const info = localesMap[cod];
        const nombreMostrado = info ? info.nombre : cod; // Si no hay info, usa el código.
        const enlace = document.createElement('a');
        enlace.href = `/local/${cod}`; // Al hacer clic, va a la página del local.
        enlace.className = 'local-btn';
        enlace.textContent = nombreMostrado;
        listaLocalesDiv.appendChild(enlace);
    });

    // Muestra el modal agregando la clase "activo".
    modalOverlay.classList.add('activo');
}

// Función para cerrar el modal.
function cerrarModal() {
    modalOverlay.classList.remove('activo');
}

// Asigna eventos a los elementos de la cuadrícula de departamentos (nuevos).
document.querySelectorAll('#nuevosDeptGrid .dept-item').forEach(item => {
    const categoria = item.getAttribute('data-categoria');
    if (categoria) {
        item.addEventListener('click', () => abrirModal(categoria));
    }
});

// Evento para cerrar el modal con el botón de cerrar.
cerrarModalBtn.addEventListener('click', cerrarModal);

// Cerrar el modal si se hace clic en el fondo oscuro.
modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) cerrarModal();
});

// Cerrar el modal con la tecla Escape.
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalOverlay.classList.contains('activo')) cerrarModal();
});

// Asigna eventos a los botones "Ver locales" que están en la barra lateral.
document.querySelectorAll('.ver-locales-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.stopPropagation(); // Evita que otros eventos se activen.
        const categoria = btn.getAttribute('data-categoria');
        if (categoria) abrirModal(categoria);
    });
});

// ======================================================================
// 10. BÚSQUEDA DE LOCAL POR CÓDIGO O NOMBRE
//     Muestra resultados en tiempo real mientras el usuario escribe.
// ======================================================================

function mostrarResultadosBusqueda(texto) {
    const resultsDiv = document.getElementById('search-results');
    if (!resultsDiv) return;

    // Si el texto está vacío, limpia los resultados y sale.
    if (!texto.trim()) {
        resultsDiv.innerHTML = '';
        return;
    }

    const textoLower = texto.trim().toUpperCase();

    // Filtra los locales cuyo código o nombre contengan el texto buscado.
    const coincidencias = todosLosLocales.filter(codigo => {
        const codMatch = codigo.toUpperCase().includes(textoLower);
        const nombre = localesMap[codigo] ? localesMap[codigo].nombre.toLowerCase() : '';
        return codMatch || nombre.includes(textoLower);
    });

    // Si no hay coincidencias, muestra un mensaje con un enlace de soporte.
    if (coincidencias.length === 0) {
        resultsDiv.innerHTML = `<div style="padding:12px; text-align:center; border:1px solid var(--accent-berry-pink); border-radius:20px; background:rgba(255,107,129,0.05); font-family: var(--font-sans); font-size: 0.8rem; color: var(--text-mist);">No se encontró el código o nombre "<strong style="color:white;">${texto}</strong>".<br>Verifique o contacte a <a href="mailto:vafersomia@gmail.com" style="color:var(--accent-berry-pink); text-decoration:none; font-weight:600;">soporte</a></div>`;
        return;
    }

    // Muestra como máximo 10 resultados.
    const mostrar = coincidencias.slice(0, 10);
    resultsDiv.innerHTML = `<div style="display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin-top:10px;">` +
        mostrar.map(cod => {
            const nombre = localesMap[cod] ? localesMap[cod].nombre : cod;
            return `<a href="/local/${cod}" class="local-result-link">${nombre} (${cod})</a>`;
        }).join('') +
        `</div>`;

    // Si hay más de 10, indica cuántos más hay.
    if (coincidencias.length > 10) {
        resultsDiv.innerHTML += `<p style="margin-top:10px; font-size:11px; text-align:center;">... y ${coincidencias.length - 10} más.</p>`;
    }
}

// Elementos del campo de búsqueda y botón.
const buscarInputLocal = document.getElementById('buscar-input');
const buscarBtnLocal = document.getElementById('buscar-btn');

// Cuando el usuario escribe en el campo, se ejecuta la búsqueda.
if (buscarInputLocal) {
    buscarInputLocal.addEventListener('input', (e) => mostrarResultadosBusqueda(e.target.value));
    buscarInputLocal.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') mostrarResultadosBusqueda(e.target.value);
    });
}

// Cuando hace clic en el botón de buscar.
if (buscarBtnLocal) {
    buscarBtnLocal.addEventListener('click', () => mostrarResultadosBusqueda(buscarInputLocal.value));
}

// ======================================================================
// 11. ANUNCIOS EN CARRUSEL (ESPECIALES Y OFERTAS)
//     Muestra anuncios que rotan automáticamente.
// ======================================================================

// Lista de anuncios especiales.
const anunciosEspeciales = [
    "Próximo evento Dia de la Madre: 10 de mayo.",
    "Nuevo horario: 9:00 a 18:00 horas."
];

// Lista de anuncios de ofertas.
const anunciosOfertas = [
    "2x1 en aguas frescas de medio litro.",
    "20% de descuento en labiales BISSÚ.",
    "Lleve 3 bolsas de bombones y pague 2.",
    "Descuento en comida para pez."
];

// Función que inicializa un carrusel de anuncios en un contenedor.
function initCarrusel(containerId, dotsId, data) {
    let index = 0;
    const container = document.getElementById(containerId);
    const dotsDiv = document.getElementById(dotsId);

    if (!container || !dotsDiv) return;

    // Crea los puntitos (indicadores) según la cantidad de anuncios.
    data.forEach((_, i) => {
        const dot = document.createElement('div');
        dot.className = `dot-anuncio ${i === 0 ? 'active' : ''}`;
        dot.onclick = () => show(i); // Al hacer clic, muestra ese anuncio.
        dotsDiv.appendChild(dot);
    });

    // Función que muestra el anuncio en la posición i.
    function show(i) {
        index = i;
        container.innerHTML = `<p class="anuncio-texto">${data[index]}</p>`;
        // Actualiza la clase "active" en los puntitos.
        Array.from(dotsDiv.children).forEach((d, idx) => {
            d.className = `dot-anuncio ${idx === i ? 'active' : ''}`;
        });
    }

    // Cambia automáticamente cada 5.5 segundos.
    setInterval(() => {
        index = (index + 1) % data.length;
        show(index);
    }, 5500);

    // Muestra el primero.
    show(0);
}

// Inicializa ambos carruseles.
initCarrusel('carrusel-especiales', 'dots-especiales', anunciosEspeciales);
initCarrusel('carrusel-ofertas', 'dots-ofertas', anunciosOfertas);

// ======================================================================
// 12. BANNER PRINCIPAL (CARRUSEL DE IMÁGENES)
//     Controla el deslizamiento de las imágenes del banner.
// ======================================================================

let currentBanner = 0;
const totalBanners = 5; // Número de slides en el banner.

const wrapperB = document.getElementById('mainCarousel');
const indicatorsDiv = document.getElementById('bannerInd');

// Crea los indicadores (puntos) para cada slide.
for (let i = 0; i < totalBanners; i++) {
    let ind = document.createElement('div');
    ind.classList.add('indicator');
    if (i === 0) ind.classList.add('active');
    ind.onclick = () => jumpToSlide(i);
    indicatorsDiv.appendChild(ind);
}

// Función que actualiza la posición del banner y los indicadores.
function updateBanner() {
    // Desplaza el wrapper horizontalmente (-20% por cada slide).
    wrapperB.style.transform = `translateX(-${currentBanner * 20}%)`;
    // Actualiza las clases de los indicadores.
    Array.from(indicatorsDiv.children).forEach((d, i) => {
        d.classList.toggle('active', i === currentBanner);
    });
}

// Salta a un slide específico.
function jumpToSlide(idx) {
    currentBanner = idx;
    updateBanner();
}

// Botones anterior y siguiente.
document.getElementById('prevBanner').addEventListener('click', () => {
    currentBanner = (currentBanner - 1 + totalBanners) % totalBanners;
    updateBanner();
});

document.getElementById('nextBanner').addEventListener('click', () => {
    currentBanner = (currentBanner + 1) % totalBanners;
    updateBanner();
});

// Cambio automático cada 8 segundos.
let bannerInterval = setInterval(() => {
    currentBanner = (currentBanner + 1) % totalBanners;
    updateBanner();
}, 8000);

// Pausa el intervalo cuando el mouse está sobre el banner.
document.querySelector('.banner-principal').addEventListener('mouseenter', () => {
    clearInterval(bannerInterval);
});

// Inicializa el banner en la posición 0.
updateBanner();

// ======================================================================
// 13. FILTROS DE SIDEBAR Y NAVEGACIÓN
//     Al hacer clic en categorías de la barra lateral o sub-nav,
//     se recargan los productos aplicando el filtro.
// ======================================================================

// Enlaces de la sub-navegación (categorías horizontales).
document.querySelectorAll('.sub-nav a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const filtro = link.getAttribute('href').split('filtro=')[1];
        if (filtro) {
            activeSubNav = filtro;
            activeSearchTerm = ""; // Limpia la búsqueda.
            document.getElementById('headerSearchInput').value = "";
            cargarProductos(); // Vuelve a cargar productos con el filtro.
            document.getElementById('discountGrid').scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Elementos de la barra lateral (categorías).
document.querySelectorAll('.sidebar-lunar .cat-item[data-sidebar]').forEach(item => {
    item.addEventListener('click', (e) => {
        // Si el clic fue en el botón "Ver locales", no hacemos nada aquí.
        if (e.target.classList.contains('ver-locales-btn')) return;

        const seccion = item.getAttribute('data-sidebar');
        if (seccion) {
            activeSubNav = seccion;
            activeSearchTerm = "";
            document.getElementById('headerSearchInput').value = "";
            cargarProductos();
            document.getElementById('discountGrid').scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// ======================================================================
// 14. INICIALIZACIÓN DE LA PÁGINA
//     Se ejecuta cuando el script se carga.
// ======================================================================

// Carga los locales desde el servidor.
cargarLocales();

// Carga los productos.
cargarProductos();

// Actualiza el contador del carrito.
actualizarContadorCarrito();

// Al hacer clic en el botón del carrito (ícono), redirige a la página del carrito.
document.getElementById('cartButton').addEventListener('click', () => {
    window.location.href = urlCarrito;
});

// Cuando se presiona "Enter" en el campo de búsqueda del header, ejecuta la búsqueda.
document.getElementById("headerSearchInput").addEventListener("keypress", function(e) {
    if (e.key === "Enter") buscarProductos();
});

// ======================================================================
// 15. FUNCIÓN DE ESCAPE PARA HTML
//     Evita inyección de código al mostrar datos del usuario.
// ======================================================================

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// ======================================================================
// 16. API AUXILIAR PARA OBTENER STOCK (no usada directamente, pero definida)
// ======================================================================

// Esta llamada es solo para "calentar" la conexión.
fetch('/api/producto-stock/1').catch(() => {});

// Función que devuelve el stock de un producto dado su ID.
window.apiProductoStock = async function(id) {
    try {
        const res = await fetch(`/api/producto-stock/${id}`);
        if (res.ok) {
            const data = await res.json();
            return data.stock;
        }
    } catch(e) {}
    return 100; // Valor por defecto.
};

// ======================================================================
// 17. REPRODUCTOR DE AUDIO (MÚSICA DE FONDO)
//     Controla la reproducción de un archivo de audio con controles básicos.
// ======================================================================

(function initMinimalAudio() {
    // Crea un objeto de audio.
    const audio = new Audio();
    audio.src = urlAudio; // La URL viene definida en el HTML.
    audio.loop = true;    // Reproduce en bucle.
    audio.preload = "auto";
    audio.volume = 0.45;  // Volumen al 45%.

    // Referencias a los elementos de la interfaz.
    const playPauseBtn = document.getElementById('playPauseBtn');
    const timerSpan = document.getElementById('audioTimer');
    const volumeSlider = document.getElementById('volumeSlider');

    let isPlaying = false;

    // Función para formatear el tiempo en minutos:segundos.
    function formatTime(seconds) {
        if (isNaN(seconds)) return "00:00";
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    // Actualiza el timer cada vez que el audio avanza.
    function updateTimer() {
        if (audio.duration && !isNaN(audio.duration)) {
            timerSpan.innerText = formatTime(audio.currentTime) + " / " + formatTime(audio.duration);
        } else {
            timerSpan.innerText = "00:00 / 00:00";
        }
    }

    audio.addEventListener('timeupdate', updateTimer);
    audio.addEventListener('loadedmetadata', updateTimer);

    // Función para reproducir/pausar.
    function togglePlay() {
        if (isPlaying) {
            audio.pause();
            playPauseBtn.innerHTML = "▶️";
        } else {
            audio.play().catch(e => {
                // Si falla, muestra un ícono de "sonido" y después vuelve a "play".
                playPauseBtn.innerHTML = "🔊";
                setTimeout(() => {
                    if (!isPlaying) playPauseBtn.innerHTML = "▶️";
                }, 800);
            });
            if (!audio.paused) playPauseBtn.innerHTML = "⏸️";
            else playPauseBtn.innerHTML = "▶️";
        }
        isPlaying = !audio.paused;
        if (audio.paused) {
            playPauseBtn.innerHTML = "▶️";
            isPlaying = false;
        } else {
            playPauseBtn.innerHTML = "⏸️";
            isPlaying = true;
        }
    }

    playPauseBtn.addEventListener('click', togglePlay);

    // Control de volumen.
    volumeSlider.addEventListener('input', (e) => {
        audio.volume = parseFloat(e.target.value);
    });
    volumeSlider.value = audio.volume;

    // Cuando el audio termina (y tiene loop activado), lo reproduce de nuevo.
    audio.addEventListener('ended', () => {
        if (audio.loop) audio.play().catch(() => {});
    });

    // Actualiza el botón según el estado de reproducción.
    audio.addEventListener('play', () => {
        playPauseBtn.innerHTML = "⏸️";
        isPlaying = true;
    });
    audio.addEventListener('pause', () => {
        playPauseBtn.innerHTML = "▶️";
        isPlaying = false;
    });

    // Si el audio ya está cargado, actualiza el timer.
    if (audio.readyState >= 1) updateTimer();
})();

// ======================================================================
// 18. ASIGNAR EVENTOS A LOS ENLACES DE CATEGORÍA EN LA BARRA DE NAVEGACIÓN
//     Hace que al hacer clic en "Comida", "Cosméticos", etc. se abra el modal.
// ======================================================================

document.querySelectorAll('.nav-categoria').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const categoria = this.getAttribute('data-categoria');
        if (categoria && typeof abrirModal === 'function') {
            abrirModal(categoria);
        } else {
            console.warn('No se encontró la función abrirModal para la categoría:', categoria);
        }
    });
});

// ======================================================================
// 19. BOTÓN "VER TODOS LOS PRODUCTOS"
//     Redirige a la página que muestra todos los productos.
// ======================================================================

document.getElementById('btnTodosProductos').addEventListener('click', function() {
    window.location.href = '/todos-productos';
});
