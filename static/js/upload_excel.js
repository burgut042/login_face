/**
 * Excel Upload System
 * Upload Excel file with person data and photos
 */

'use strict';

// ==================== Configuration ====================
const CONFIG = {
    API: {
        UPLOAD_ENDPOINT: '/api/upload-excel/',
        TIMEOUT: 300000, // 5 minutes for large files
    },
    FILE: {
        MAX_SIZE: 50 * 1024 * 1024, // 50MB
        ALLOWED_TYPES: [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]
    }
};

// ==================== DOM Elements ====================
const DOM = {
    dropZone: document.getElementById('dropZone'),
    fileInput: document.getElementById('fileInput'),
    uploadBtn: document.getElementById('uploadBtn'),
    progressSection: document.getElementById('progressSection'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    resultsSection: document.getElementById('resultsSection'),
    successCount: document.getElementById('successCount'),
    errorCount: document.getElementById('errorCount'),
    totalCount: document.getElementById('totalCount'),
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage')
};

// ==================== State ====================
let selectedFile = null;

// ==================== Toast Notification ====================
function showToast(message, type = 'info') {
    DOM.toastMessage.textContent = message;
    DOM.toast.className = 'toast show';

    if (type === 'success') {
        DOM.toast.style.background = 'linear-gradient(135deg, #10b981, #059669)';
    } else if (type === 'error') {
        DOM.toast.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
    } else if (type === 'warning') {
        DOM.toast.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
    } else {
        DOM.toast.style.background = 'linear-gradient(135deg, #6366f1, #4f46e5)';
    }

    setTimeout(() => {
        DOM.toast.classList.remove('show');
    }, 3000);
}

// ==================== File Validation ====================
function validateFile(file) {
    // Check file type
    const fileName = file.name.toLowerCase();
    const isExcel = fileName.endsWith('.xlsx') || fileName.endsWith('.xls');
    const isWord = fileName.endsWith('.docx');

    if (!isExcel && !isWord) {
        showToast('❌ Faqat Excel (.xlsx, .xls) yoki Word (.docx) fayllari qabul qilinadi', 'error');
        return false;
    }

    // Check file size
    if (file.size > CONFIG.FILE.MAX_SIZE) {
        showToast('❌ Fayl hajmi juda katta (max 50MB)', 'error');
        return false;
    }

    return true;
}

// ==================== File Selection ====================
function handleFileSelect(file) {
    if (!validateFile(file)) {
        return;
    }

    selectedFile = file;
    DOM.uploadBtn.disabled = false;
    DOM.dropZone.innerHTML = `
        <div class="drop-icon">✅</div>
        <div class="drop-text">${file.name}</div>
        <div class="drop-subtext">Hajm: ${(file.size / 1024 / 1024).toFixed(2)} MB</div>
    `;
    showToast(`📊 ${file.name} tanlandi`, 'success');
}

// ==================== Drag & Drop ====================
DOM.dropZone.addEventListener('click', () => {
    DOM.fileInput.click();
});

DOM.fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFileSelect(file);
    }
});

DOM.dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    DOM.dropZone.classList.add('dragover');
});

DOM.dropZone.addEventListener('dragleave', () => {
    DOM.dropZone.classList.remove('dragover');
});

DOM.dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    DOM.dropZone.classList.remove('dragover');

    const file = e.dataTransfer.files[0];
    if (file) {
        handleFileSelect(file);
    }
});

// ==================== Upload & Process ====================
async function uploadExcel() {
    if (!selectedFile) {
        showToast('❌ Iltimos, fayl tanlang', 'error');
        return;
    }

    try {
        // Disable upload button
        DOM.uploadBtn.disabled = true;
        DOM.uploadBtn.innerHTML = '⏳ Yuklanmoqda...';

        // Show progress
        DOM.progressSection.style.display = 'block';
        DOM.resultsSection.style.display = 'none';

        // Create FormData
        const formData = new FormData();
        formData.append('excel_file', selectedFile);

        // Upload with progress
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                DOM.progressBar.style.width = percent + '%';
                DOM.progressBar.textContent = percent + '%';
                DOM.progressText.textContent = 'Fayl yuklanmoqda...';
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                try {
                    const result = JSON.parse(xhr.responseText);
                    handleUploadSuccess(result);
                } catch (error) {
                    console.error('Parse error:', error);
                    showToast('❌ Javobni qayta ishlashda xatolik', 'error');
                    resetUploadState();
                }
            } else {
                try {
                    const error = JSON.parse(xhr.responseText);
                    showToast(`❌ ${error.error || 'Xatolik yuz berdi'}`, 'error');
                } catch {
                    showToast('❌ Server xatolik qaytardi', 'error');
                }
                resetUploadState();
            }
        });

        xhr.addEventListener('error', () => {
            showToast('❌ Tarmoq xatoligi', 'error');
            resetUploadState();
        });

        xhr.addEventListener('abort', () => {
            showToast('⚠️ Yuklash bekor qilindi', 'warning');
            resetUploadState();
        });

        xhr.open('POST', CONFIG.API.UPLOAD_ENDPOINT, true);
        xhr.send(formData);

    } catch (error) {
        console.error('Upload error:', error);
        showToast('❌ Yuklashda xatolik', 'error');
        resetUploadState();
    }
}

// ==================== Handle Success ====================
function handleUploadSuccess(result) {
    console.log('Upload result:', result);

    // Update progress
    DOM.progressBar.style.width = '100%';
    DOM.progressBar.textContent = '100%';
    DOM.progressText.textContent = 'Bajarildi!';

    // Show results
    setTimeout(() => {
        DOM.progressSection.style.display = 'none';
        DOM.resultsSection.style.display = 'block';

        DOM.successCount.textContent = result.success_count || 0;
        DOM.errorCount.textContent = result.error_count || 0;
        DOM.totalCount.textContent = result.total_processed || 0;

        // Display uploaded persons
        if (result.uploaded_persons && result.uploaded_persons.length > 0) {
            displayUploadedPersons(result.uploaded_persons);
        }

        if (result.success_count > 0) {
            showToast(`✅ ${result.success_count} ta shaxs muvaffaqiyatli qo'shildi!`, 'success');
        }

        if (result.error_count > 0) {
            showToast(`⚠️ ${result.error_count} ta xatolik bor. Console'ni tekshiring.`, 'warning');
            console.log('Errors:', result.errors);
        }
    }, 500);
}

// ==================== Display Uploaded Persons ====================
function displayUploadedPersons(persons) {
    const resultsSection = DOM.resultsSection;

    // Create persons list HTML
    let personsHTML = `
        <div style="margin-top: 2rem; padding: 1.5rem; background: var(--bg-elevated); border-radius: 12px;">
            <h3 style="color: var(--text-primary); margin-bottom: 1rem; font-size: 1.2rem;">
                📋 Yuklangan Shaxslar
            </h3>
            <div style="max-height: 400px; overflow-y: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: var(--bg-dark); border-bottom: 2px solid var(--border);">
                            <th style="padding: 0.75rem; text-align: left; color: var(--primary);">ID</th>
                            <th style="padding: 0.75rem; text-align: left; color: var(--primary);">Rasm</th>
                            <th style="padding: 0.75rem; text-align: left; color: var(--primary);">FIO</th>
                            <th style="padding: 0.75rem; text-align: center; color: var(--primary);">Holat</th>
                        </tr>
                    </thead>
                    <tbody>
    `;

    persons.forEach((person, index) => {
        const statusBadge = person.is_new
            ? '<span style="background: #10b981; color: white; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.85rem;">Yangi</span>'
            : '<span style="background: #f59e0b; color: white; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.85rem;">Yangilandi</span>';

        const photoHTML = person.photo_url
            ? `<img src="${person.photo_url}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid var(--primary);" />`
            : '<div style="width: 40px; height: 40px; border-radius: 50%; background: var(--bg-dark); display: flex; align-items: center; justify-content: center;">👤</div>';

        personsHTML += `
            <tr style="border-bottom: 1px solid var(--border); ${index % 2 === 0 ? 'background: var(--bg-card);' : ''}">
                <td style="padding: 0.75rem; color: var(--text-secondary);">#${person.id}</td>
                <td style="padding: 0.75rem;">${photoHTML}</td>
                <td style="padding: 0.75rem;">
                    <div style="color: var(--text-primary); font-weight: 600;">${person.full_name}</div>
                    ${person.rank ? `<div style="color: var(--text-secondary); font-size: 0.85rem;">${person.rank}</div>` : ''}
                </td>
                <td style="padding: 0.75rem; text-align: center;">${statusBadge}</td>
            </tr>
        `;
    });

    personsHTML += `
                    </tbody>
                </table>
            </div>
        </div>
    `;

    // Insert before buttons
    const buttons = resultsSection.querySelector('div[style*="text-align: center"]');
    buttons.insertAdjacentHTML('beforebegin', personsHTML);
}

// ==================== Reset State ====================
function resetUploadState() {
    DOM.uploadBtn.disabled = false;
    DOM.uploadBtn.innerHTML = '📤 Yuklash va Import Qilish';
    DOM.progressSection.style.display = 'none';
}

// ==================== Upload Button ====================
DOM.uploadBtn.addEventListener('click', uploadExcel);

// ==================== Console Info ====================
console.log('📊 Excel Upload System initialized');
console.log('Max file size:', CONFIG.FILE.MAX_SIZE / 1024 / 1024, 'MB');
