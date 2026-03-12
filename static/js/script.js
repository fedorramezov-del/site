document.addEventListener('DOMContentLoaded', () => {

    // =====================================
    // УТИЛИТА: получить accent-color в rgba
    // =====================================
    function getAccentRGBA(opacity) {
        const accent = getComputedStyle(document.documentElement)
            .getPropertyValue('--accent-color')
            .trim();

        if (!accent.startsWith("#")) return accent;

        const hex = accent.replace('#', '');
        const bigint = parseInt(hex, 16);

        const r = (bigint >> 16) & 255;
        const g = (bigint >> 8) & 255;
        const b = bigint & 255;

        return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    }

    // =====================================
    // 1. Авто-скрытие flash
    // =====================================
    document.querySelectorAll('.flash').forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transition = 'opacity 0.5s ease';
            setTimeout(() => flash.remove(), 500);
        }, 5000);
    });

    // =====================================
    // 2. Активный пункт меню
    // =====================================
    const currentPath = window.location.pathname;
    document.querySelectorAll('nav a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // =====================================
    // 3. Динамическая граница блоков
    // =====================================
    document.querySelectorAll('.action-btn').forEach(button => {

        button.addEventListener('mousedown', () => {
            button.style.transform = 'scale(0.95)';
        });

        button.addEventListener('mouseup', () => {
            button.style.transform = 'scale(1)';
        });

        button.addEventListener('mouseenter', () => {

            const parentBlock = button.closest('.file-batch');
            if (!parentBlock) return;

            const accent = getComputedStyle(document.documentElement)
                .getPropertyValue('--accent-color')
                .trim();

            parentBlock.style.setProperty('--dynamic-border', accent);
            parentBlock.classList.add('dynamic-border-active');
        });

        button.addEventListener('mouseleave', () => {
            const parentBlock = button.closest('.file-batch');
            if (!parentBlock) return;

            parentBlock.classList.remove('dynamic-border-active');
        });
    });

    // =====================================
// DRAG & DROP
// =====================================
const fileInput = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');

if (dropZone && fileInput) {

    dropZone.addEventListener('click', (e) => {

    if (
        e.target.tagName === "TEXTAREA" ||
        e.target.tagName === "INPUT" ||
        e.target.tagName === "BUTTON"
    ) {
        return;
    }

    fileInput.click();
});

    ['dragenter', 'dragover'].forEach(event => {
        dropZone.addEventListener(event, e => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('drag-active');
        });
    });

    ['dragleave', 'drop'].forEach(event => {
        dropZone.addEventListener(event, e => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-active');
        });
    });

    dropZone.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        fileInput.files = files;
        handleFileSelect(files);
    });

    fileInput.addEventListener('change', e => {
        handleFileSelect(e.target.files);
    });
}


    // =====================================
    // 5. THEME DROPDOWN
    // =====================================
    const themeBtn = document.getElementById('theme-toggle-btn');
    const dropdown = document.getElementById('theme-dropdown');

    if (themeBtn && dropdown) {

        themeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.style.display =
                dropdown.style.display === 'block' ? 'none' : 'block';
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('#theme-dropdown') &&
                !e.target.closest('#theme-toggle-btn')) {
                dropdown.style.display = 'none';
            }
        });
    }

    // =====================================
    // 6. THEME SWITCHER
    // =====================================
    const themeOptions = document.querySelectorAll('.theme-option');

    themeOptions.forEach(option => {
        option.addEventListener('click', async () => {

            const selectedTheme = option.dataset.theme;

            // применяем тему мгновенно
            document.documentElement.setAttribute('data-theme', selectedTheme);

            if (dropdown) dropdown.style.display = 'none';

            try {
                await fetch("/set_theme", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": document
                            .querySelector('meta[name="csrf-token"]')
                            ?.content
                    },
                    body: JSON.stringify({ theme: selectedTheme })
                });
            } catch (err) {
                console.error("Проблема с загрузкой темы:", err);
            }
        });
    });

// =====================================
// PREVIEW FILES
// =====================================
function handleFileSelect(files) {

    const previewContainer = document.getElementById('preview-container');
    const fileNameSpan = document.getElementById('file-name');

    if (!previewContainer || !fileNameSpan) return;

    previewContainer.innerHTML = '';

    if (!files || files.length === 0) {
        fileNameSpan.textContent = "Файлы не выбраны";
        return;
    }

    fileNameSpan.textContent = "Выбрано файлов: " + files.length;

    Array.from(files).forEach(file => {

        const fileCard = document.createElement('div');
        fileCard.style.display = "flex";
        fileCard.style.alignItems = "center";
        fileCard.style.gap = "10px";
        fileCard.style.padding = "8px";
        fileCard.style.marginBottom = "8px";
        fileCard.style.borderRadius = "8px";
        fileCard.style.background = "rgba(255,255,255,0.03)";
        fileCard.style.border = "1px solid var(--glass-border)";

        const ext = file.name.split('.').pop().toLowerCase();

        // ИКОНКИ ПО ТИПУ
        const icon = document.createElement('div');
        icon.style.fontSize = "22px";

        if (["png","jpg","jpeg","gif","webp"].includes(ext)) {
            icon.innerHTML = "🖼";
        } else if (["pdf"].includes(ext)) {
            icon.innerHTML = "📕";
        } else if (["zip","rar","7z"].includes(ext)) {
            icon.innerHTML = "🗜";
        } else if (["txt","doc","docx"].includes(ext)) {
            icon.innerHTML = "📄";
        } else {
            icon.innerHTML = "📁";
        }

        fileCard.appendChild(icon);

        // ПРЕДПРОСМОТР ИЗОБРАЖЕНИЯ
        if (["png","jpg","jpeg","gif","webp"].includes(ext)) {

            const img = document.createElement('img');
            img.style.maxWidth = "60px";
            img.style.maxHeight = "60px";
            img.style.borderRadius = "6px";
            img.style.objectFit = "cover";

            const reader = new FileReader();
            reader.onload = e => img.src = e.target.result;
            reader.readAsDataURL(file);

            fileCard.appendChild(img);
        }

        const fileInfo = document.createElement('div');
        fileInfo.style.flex = "1";
        fileInfo.style.fontSize = "0.9rem";
        fileInfo.textContent = file.name;

        fileCard.appendChild(fileInfo);

        previewContainer.appendChild(fileCard);
    });
}

// ==============================
// THEME BUILDER
// ==============================

const builder = document.getElementById("theme-builder");
const accentInput = document.getElementById("tb-accent");
const bgInput = document.getElementById("tb-bg");
const containerInput = document.getElementById("tb-container");
const saveBtn = document.getElementById("save-custom-theme");

// показываем builder если выбрали custom
document.querySelectorAll('.theme-option').forEach(option => {
    option.addEventListener("click", () => {
        if (option.dataset.theme === "custom") {
            builder.style.display = "flex";
        } else {
            builder.style.display = "none";
        }
    });
});

// LIVE PREVIEW
function applyCustomTheme() {
    document.documentElement.style.setProperty("--custom-accent", accentInput.value);
    document.documentElement.style.setProperty("--custom-bg", bgInput.value);
    document.documentElement.style.setProperty("--custom-container", containerInput.value);
}

if (accentInput && bgInput && containerInput) {

    accentInput.addEventListener("input", applyCustomTheme);
    bgInput.addEventListener("input", applyCustomTheme);
    containerInput.addEventListener("input", applyCustomTheme);
}

// SAVE TO SERVER
if (saveBtn) {
    saveBtn.addEventListener("click", async () => {

        saveBtn.classList.add("loading-btn");
        saveBtn.disabled = true;

        const themeData = {
            theme: "custom",
            accent: accentInput.value,
            bg: bgInput.value,
            container: containerInput.value
        };

        try {
            await fetch("/set_theme", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": document
                        .querySelector('meta[name="csrf-token"]')
                        ?.content
                },
                body: JSON.stringify(themeData)
            });

            showToast("Тема сохранена 💾", "success");

        } catch (err) {

            showToast("Ошибка сохранения темы ❌", "error");
            console.error("Theme save error:", err);

        } finally {
            saveBtn.classList.remove("loading-btn");
            saveBtn.disabled = false;
        }
    });
}
// =====================================
// MICRO-FEEDBACK: TOAST SYSTEM
// =====================================

function showToast(message, type = "success") {

    let container = document.getElementById("toast-container");

    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerText = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 4000);
}
// =====================================
// FLASH → TOAST
// =====================================

document.querySelectorAll(".flash").forEach(flash => {

    const type = flash.classList.contains("error") ? "error" : "success";
    showToast(flash.innerText, type);

    flash.remove();
});
// =====================================
// FORM LOADING STATE
// =====================================

document.querySelectorAll("form").forEach(form => {

    form.addEventListener("submit", function () {

        const btn = form.querySelector("button[type='submit']");

        if (btn) {
            btn.classList.add("loading-btn");
            btn.disabled = true;
        }
    });
});


}); // ← закрытие DOMContentLoaded


