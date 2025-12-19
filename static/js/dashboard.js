/**
 * Emotion  System - Main Application
 * Professional JavaScript Module for AI-powered emotion recognition
 *
 * @author Senior Frontend Developer
 * @version 2.0.0
 * @description Real-time emotion  using webcam and AI API
 */

'use strict';

// ==================== Configuration ====================
const CONFIG = {
    API: {
        DETECT_ENDPOINT: '/api/detect-emotion/',
        SAVE_ENDPOINT: '/api/save-emotion/',
        CAPTURE_ENDPOINT: '/api/capture-face/',
        TIMEOUT: 5000,
        RETRY_ATTEMPTS: 3
    },
    DETECTION: {
        INTERVAL: 1000,  // 1 soniya (tezroq aniqlash)
        REQUIRED_SAMPLES: 5,
        VIDEO_WIDTH: 640,  // Kichikroq o'lcham (tezroq)
        VIDEO_HEIGHT: 480,  // Kichikroq o'lcham (tezroq)
        IMAGE_QUALITY: 0.6  // Pastroq sifat (tezroq)
    },
    UI: {
        TOAST_DURATION: 3000,
        ANIMATION_DURATION: 500,
        HISTORY_MAX_ITEMS: 20
    }
};

// ==================== Emotion Data ====================
// Backend EMOTION_UZ bilan to'liq mos keladi
const EMOTIONS = {
    happy: {
        uz: 'HURSAND',
        en: 'Happy',
        icon: '😊',
        color: '#10b981',
        gradient: 'linear-gradient(135deg, #10b981, #059669)'
    },
    sad: {
        uz: 'CHARCHOQ (JISMONIY/RUHIY)',
        en: 'Sad',
        icon: '😢',
        color: '#6366f1',
        gradient: 'linear-gradient(135deg, #6366f1, #4f46e5)'
    },
    neutral: {
        uz: 'BARQAROR (HOTIRJAM)',
        en: 'Neutral',
        icon: '😐',
        color: '#64748b',
        gradient: 'linear-gradient(135deg, #64748b, #475569)'
    },
    angry: {
        uz: 'TAJAVUZLIK (ASABIY)',
        en: 'Angry',
        icon: '😠',
        color: '#ef4444',
        gradient: 'linear-gradient(135deg, #ef4444, #dc2626)'
    },
    surprise: {
        uz: 'NOSTANDART (STRESS)',
        en: 'Surprise',
        icon: '😲',
        color: '#f59e0b',
        gradient: 'linear-gradient(135deg, #f59e0b, #d97706)'
    },
    fear: {
        uz: "QO'RQUV (HAVOTIR)",
        en: 'Fear',
        icon: '😨',
        color: '#8b5cf6',
        gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)'
    },
    disgust: {
        uz: 'JIRKANISH',
        en: 'Disgust',
        icon: '🤢',
        color: '#ec4899',
        gradient: 'linear-gradient(135deg, #ec4899, #db2777)'
    }
};

// ==================== Application State ====================
class AppState {
    constructor() {
        this.detectionInterval = null;
        this.timeInterval = null;
        this.startTime = null;
        this.scanCount = 0;
        this.history = [];
        this.isDetecting = false;
        this.detectionBuffer = [];  // Buffer for 5 samples
        this.currentSessions = 0;
        this.currentPerson = null;  // Currently recognized person
        this.personHistory = [];  // History for current person only
        this.lastPersonId = null;  // Track person changes
        this.isPaused = false;  // Pause detection when person modal is shown
        this.currentEmotionData = null;  // Store current emotion for saving on continue
        this.waitingForNewPerson = false;  // Continue bosilgandan keyin yangi shaxsni kutish
    }



    reset() {
        this.clearIntervals();
        this.scanCount = 0;
        this.history = [];
        this.isDetecting = false;
        this.detectionBuffer = [];
        this.currentSessions = 0;
        this.currentPerson = null;
        this.personHistory = [];
        this.lastPersonId = null;
        this.isPaused = false;  // TUZATILDI: false bo'lishi kerak
        this.waitingForNewPerson = false;
        this.currentEmotionData = null;
    }

    pause() {
        console.log('🔴🔴🔴 PAUSE() funksiyasi ichida - OLDIN this.isPaused =', this.isPaused);
        this.isPaused = true;
        console.log('🔴🔴🔴 PAUSE() funksiyasi ichida - KEYIN this.isPaused =', this.isPaused);
        console.log('⏸️ Detection paused - waiting for user confirmation');
    }

    resume() {
        this.isPaused = false;  // TUZATILDI: Detection davom etishi uchun false bo'lishi kerak
        this.waitingForNewPerson = true;  // Yangi shaxsni kutish
        console.log('▶️ Detection resumed - waiting for new person');
    }

    resetPersonHistory() {
        this.personHistory = [];
        this.detectionBuffer = [];
        console.log('🔄 Shaxs tarixi tozalandi');
    }

    add(emotion, confidence) {
        this.detectionBuffer.push({ emotion, confidence });
        this.currentSessions++;

        // Keep only last 5 samples
        if (this.detectionBuffer.length > CONFIG.DETECTION.REQUIRED_SAMPLES) {
            this.detectionBuffer.shift();
        }

        return this.detectionBuffer.length >= CONFIG.DETECTION.REQUIRED_SAMPLES;
    }

    getSamplesForSave() {
        return this.detectionBuffer.slice();  // Return copy
    }

    clearBuffer() {
        this.detectionBuffer = [];
    }

    clearIntervals() {
        if (this.detectionInterval) {
            clearInterval(this.detectionInterval);
            this.detectionInterval = null;
        }
        if (this.timeInterval) {
            clearInterval(this.timeInterval);
            this.timeInterval = null;
        }
    }
}

// ==================== DOM Elements Manager ====================
class DOMManager {
    constructor() {
        this.elements = {
            // Video Elements
            video: document.getElementById('videoElement'),
            videoOverlay: document.getElementById('videoOverlay'),
            loadingOverlay: document.getElementById('loadingOverlay'),

            // Control Elements
            startBtn: document.getElementById('startBtn'),
            stopBtn: document.getElementById('stopBtn'),
            statusDot: document.getElementById('statusDot'),
            statusText: document.getElementById('statusText'),

            // Emotion Display Elements
            emotionIcon: document.getElementById('emotionIcon'),
            emotionName: document.getElementById('emotionName'),
            emotionUzbek: document.getElementById('emotionUzbek'),
            confidenceValue: document.getElementById('confidenceValue'),
            confidenceFill: document.getElementById('confidenceFill'),
            emotionActions: document.getElementById('emotionActions'),
            emotionContinueBtn: document.getElementById('emotionContinueBtn'),
            emotionTestBtn: document.getElementById('emotionTestBtn'),
            emotionPersonPhotoWrapper: document.getElementById('emotionPersonPhotoWrapper'),
            emotionPersonPhoto: document.getElementById('emotionPersonPhoto'),
            emotionPersonName: document.getElementById('emotionPersonName'),

            // Stats Elements
            totalScans: document.getElementById('totalScans'),
            sessionTime: document.getElementById('sessionTime'),

            // History Elements
            historyList: document.getElementById('historyList'),

            // Person Recognition Elements
            personCard: document.getElementById('personCard'),
            personPhoto: document.getElementById('personPhoto'),
            personName: document.getElementById('personName'),
            personFaceConfidence: document.getElementById('personFaceConfidence'),
            personEmotionCount: document.getElementById('personEmotionCount'),
            personInfo: document.getElementById('personInfo'),
            cameraOffMessage: document.getElementById('cameraOffMessage'),
            noPersonMessage: document.getElementById('noPersonMessage'),
            dashboardGrid: document.querySelector('.dashboard-grid'),

            // Person Emotion Elements (inside person card)
            personEmotionSection: document.getElementById('personEmotionSection'),
            personEmotionIcon: document.getElementById('personEmotionIcon'),
            personEmotionName: document.getElementById('personEmotionName'),
            personEmotionUzbek: document.getElementById('personEmotionUzbek'),
            personConfidenceValue: document.getElementById('personConfidenceValue'),
            personConfidenceFill: document.getElementById('personConfidenceFill'),

            // Toast Elements
            toast: document.getElementById('toast'),
            toastMessage: document.getElementById('toastMessage'),

            // Testing Modal Elements
            testingOverlay: document.getElementById('testingOverlay'),
            testingPersonName: document.getElementById('testingPersonName'),
            testingNegativeCount: document.getElementById('testingNegativeCount'),
            testingTotalCount: document.getElementById('testingTotalCount'),
            testingPercentage: document.getElementById('testingPercentage'),
            confirmTestingBtn: document.getElementById('confirmTestingBtn'),
            confirmNormalBtn: document.getElementById('confirmNormalBtn'),
            modalPersonPhoto: document.getElementById('modalPersonPhoto'),
            resultIcon: document.getElementById('resultIcon'),
            resultTitle: document.getElementById('resultTitle'),
            resultDescription: document.getElementById('resultDescription'),
            testingWarningBadge: document.getElementById('testingWarningBadge'),

            // Person Recognition Modal Elements
            personRecognitionOverlay: document.getElementById('personRecognitionOverlay'),
            recognitionPersonPhoto: document.getElementById('recognitionPersonPhoto'),
            recognitionPersonName: document.getElementById('recognitionPersonName'),
            recognitionFaceConfidence: document.getElementById('recognitionFaceConfidence'),
            recognitionEmotionCount: document.getElementById('recognitionEmotionCount'),
            continueRecognitionBtn: document.getElementById('continueRecognitionBtn'),
            sendToTestingBtn: document.getElementById('sendToTestingBtn')
        };

        this.validateElements();
    }

    validateElements() {
        Object.entries(this.elements).forEach(([key, element]) => {
            if (!element) {
                console.error('Element not found: ${key}');
            }
        });
    }

    get(elementKey) {
        return this.elements[elementKey];
    }
}

// ==================== UI Controller ====================
class UIController {
    constructor(domManager) {
        this.dom = domManager;
    }

    showLoading() {
        this.dom.get('loadingOverlay').classList.add('visible');
    }

    hideLoading() {
        this.dom.get('loadingOverlay').classList.remove('visible');
    }

    showVideoOverlay() {
        this.dom.get('videoOverlay').classList.remove('hidden');
    }

    hideVideoOverlay() {
        this.dom.get('videoOverlay').classList.add('hidden');
    }

    updateStatus(isActive) {
        const statusDot = this.dom.get('statusDot');
        const statusText = this.dom.get('statusText');

        if (isActive) {
            statusDot.classList.add('active');
            statusText.textContent = 'Tizim faol - hissiyotlar aniqlanmoqda';
        } else {
            statusDot.classList.remove('active');
            statusText.textContent = 'Tizim kutish rejimida';
        }
    }

    enableControls(start, stop) {
        this.dom.get('startBtn').disabled = !start;
        this.dom.get('stopBtn').disabled = !stop;
    }

    updateEmotion(emotion, confidence, showButtons = false, personData = null) {
        const emotionData = EMOTIONS[emotion] || EMOTIONS.neutral;

        this.dom.get('emotionIcon').textContent = emotionData.icon;
        this.dom.get('emotionName').textContent = emotionData.en;
        this.dom.get('emotionUzbek').textContent = emotionData.uz;
        this.dom.get('confidenceValue').textContent = `${Math.round(confidence)}%`;
        this.dom.get('confidenceFill').style.width = `${confidence}%`;

        // Update gradient color
        const emotionNameEl = this.dom.get('emotionName');
        emotionNameEl.style.background = emotionData.gradient;
        emotionNameEl.style.webkitBackgroundClip = 'text';
        emotionNameEl.style.webkitTextFillColor = 'transparent';

        // Show/hide person photo and name
        if (personData) {
            this.dom.get('emotionPersonPhoto').src = personData.photo_url || '';
            this.dom.get('emotionPersonName').textContent = personData.full_name || '';
            this.dom.get('emotionPersonPhotoWrapper').style.display = 'block';
        } else {
            this.dom.get('emotionPersonPhotoWrapper').style.display = 'none';
        }

        // Show/hide action buttons
        if (showButtons) {
            this.dom.get('emotionActions').style.display = 'flex';
        } else {
            this.dom.get('emotionActions').style.display = 'none';
        }
    }

    updatePersonCard(personData) {
        if (!personData) {
            // No  - show "no person" message
            this.showNoPersonMessage();
            return;
        }

        // Handle different person states
        const status = personData.status || 'unknown';

        switch (status) {
            case 'not_registered':
                // Person detected but not in database
                this.showNotRegisteredMessage(personData.message);
                break;

            case 'active':
                // Person active, always detect emotions
                this.showActivePerson(personData);
                break;

            default:
                this.showNoPersonMessage();
        }
    }

    showNotRegisteredMessage(message) {
        // Hide all sections
        this.dom.get('personInfo').style.display = 'none';
        this.dom.get('cameraOffMessage').style.display = 'none';
        this.dom.get('personEmotionSection').style.display = 'none';

        // Show custom "not registered" message
        const noPersonMsg = this.dom.get('noPersonMessage');
        noPersonMsg.style.display = 'flex';
        noPersonMsg.innerHTML = `
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>
            <p style="color: #f59e0b;">Bazada mavjud emas</p>
            <small>${message || "Bu shaxs bazada ro'yxatdan o'tmagan"}</small>
        `;
    }

    showActivePerson(personData) {
        // Show person info
        this.dom.get('personPhoto').src = personData.photo_url;
        this.dom.get('personPhoto').alt = personData.full_name;
        this.dom.get('personName').textContent = personData.full_name;
        this.dom.get('personFaceConfidence').textContent = `${personData.confidence || 0}%`;
        this.dom.get('personEmotionCount').textContent = `${personData.camera_logs_count}/5`;

        // Show person info, hide messages
        this.dom.get('personInfo').style.display = 'block';
        this.dom.get('cameraOffMessage').style.display = 'none';
        this.dom.get('noPersonMessage').style.display = 'none';
    }

    showNoPersonMessage() {
        // Camera is on, but no person detected
        this.dom.get('personInfo').style.display = 'none';
        this.dom.get('cameraOffMessage').style.display = 'none';
        this.dom.get('personEmotionSection').style.display = 'none';

        const noPersonMsg = this.dom.get('noPersonMessage');
        noPersonMsg.style.display = 'flex';
        noPersonMsg.innerHTML = `
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
            </svg>
            <p>Shaxs tanilmadi</p>
            <small>Kamerada ro'yxatdan o'tgan shaxs ko'rining</small>
        `;
    }

    showCameraOffMessage() {
        // Camera is OFF - show camera off message
        this.dom.get('personInfo').style.display = 'none';
        this.dom.get('noPersonMessage').style.display = 'none';
        this.dom.get('cameraOffMessage').style.display = 'flex';
        this.dom.get('personEmotionSection').style.display = 'none';

        // Clear person photo and info when camera stops
        this.dom.get('personPhoto').src = '';
        this.dom.get('personPhoto').alt = '';
        this.dom.get('personName').textContent = '---';
        this.dom.get('personFaceConfidence').textContent = '0%';
        this.dom.get('personEmotionCount').textContent = '0';
    }

    updatePersonEmotion(emotion, confidence) {
        const emotionData = EMOTIONS[emotion] || EMOTIONS.neutral;

        // Show emotion section
        this.dom.get('personEmotionSection').style.display = 'block';

        // Update emotion display inside person card
        this.dom.get('personEmotionIcon').textContent = emotionData.icon;
        this.dom.get('personEmotionName').textContent = emotionData.en;
        this.dom.get('personEmotionUzbek').textContent = emotionData.uz;
        this.dom.get('personConfidenceValue').textContent = `${Math.round(confidence)}%`;
        this.dom.get('personConfidenceFill').style.width = `${confidence}%`;

        // Update gradient color
        const emotionNameEl = this.dom.get('personEmotionName');
        emotionNameEl.style.background = emotionData.gradient;
        emotionNameEl.style.webkitBackgroundClip = 'text';
        emotionNameEl.style.webkitTextFillColor = 'transparent';
    }


    updateStats(scanCount, sessionTime) {
        this.dom.get('totalScans').textContent = scanCount;
        this.dom.get('sessionTime').textContent = sessionTime;
    }

    renderHistory(historyItems, personName = null) {
        const historyList = this.dom.get('historyList');

        if (historyItems.length === 0) {
            const waitingMessage = personName
                ? `${personName} uchun aniqlash kutilmoqda...`
                : 'Aniqlash kutilmoqda...';

            historyList.innerHTML = `
                <div class="history-item">
                    <span class="history-emotion">${waitingMessage}</span>
                    <div class="history-meta">
                        <span class="history-time">--:--:--</span>
                    </div>
                </div>
            `;
            return;
        }

        historyList.innerHTML = historyItems.map((item, index) => {
            const count = historyItems.length - index;
            const isLast = index === 0;
            const itemClass = isLast ? 'history-item history-item-latest' : 'history-item';

            return `
                <div class="${itemClass}">
                    <span class="history-emotion">
                        ${item.emotionData.icon} ${item.emotionData.en} (${item.emotionData.uz})
                    </span>
                    <div class="history-meta">
                        <span class="history-count">${count}/5</span>
                        <span class="history-confidence">${item.confidence}%</span>
                        <span class="history-time">${item.time}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    showToast(message, type = 'info') {
        const toast = this.dom.get('toast');
        const toastMessage = this.dom.get('toastMessage');

        toast.className = `toast ${type}`;
        toastMessage.textContent = message;
        toast.classList.add('show');

        setTimeout(() => {
            toast.classList.remove('show');
        }, CONFIG.UI.TOAST_DURATION);
    }

    showResultsModal(personData, emotionAnalysis, requiresTesting) {
        const overlay = this.dom.get('testingOverlay');

        // Set person photo
        this.dom.get('modalPersonPhoto').src = personData.photo_url || '';
        this.dom.get('modalPersonPhoto').alt = personData.full_name;

        // Set person name
        this.dom.get('testingPersonName').textContent = personData.full_name;

        // Set statistics
        if (emotionAnalysis) {
            this.dom.get('testingNegativeCount').textContent = emotionAnalysis.negative_count;
            this.dom.get('testingTotalCount').textContent = emotionAnalysis.total_emotions;
            this.dom.get('testingPercentage').textContent = `${emotionAnalysis.negative_percentage}%`;
        }

        // Update modal appearance based on testing requirement
        if (requiresTesting) {
            // Warning style for testing required
            this.dom.get('resultIcon').textContent = '⚠️';
            this.dom.get('resultTitle').textContent = 'Diqqat! Test Talab Qilinadi';
            this.dom.get('resultDescription').textContent = 'Salbiy emotionlar yuqori darajada aniqlandi.';
            this.dom.get('testingWarningBadge').style.display = 'flex';
            this.dom.get('confirmTestingBtn').style.background = '#ef4444'; // Red highlight
        } else {
            // Success style for normal confirmation
            this.dom.get('resultIcon').textContent = '✅';
            this.dom.get('resultTitle').textContent = 'Natijalar Tayyor';
            this.dom.get('resultDescription').textContent = 'Hodim uchun barcha ma\'lumotlar to\'plandi.';
            this.dom.get('testingWarningBadge').style.display = 'none';
            this.dom.get('confirmTestingBtn').style.background = '#f59e0b'; // Default warning color
        }

        overlay.classList.add('active');
        console.log(`📊 Natijalar modali ko'rsatildi: ${personData.full_name} (Test: ${requiresTesting})`);
    }

    hideResultsModal() {
        const overlay = this.dom.get('testingOverlay');
        overlay.classList.remove('active');
    }

    showPersonRecognitionModal(personData) {
        const overlay = this.dom.get('personRecognitionOverlay');

        // Set person photo
        this.dom.get('recognitionPersonPhoto').src = personData.photo_url || '';
        this.dom.get('recognitionPersonPhoto').alt = personData.full_name;

        // Set person name
        this.dom.get('recognitionPersonName').textContent = personData.full_name;

        // Set details
        this.dom.get('recognitionFaceConfidence').textContent = `${personData.confidence || 0}%`;
        this.dom.get('recognitionEmotionCount').textContent = `${personData.camera_logs_count}/5`;

        overlay.classList.add('active');
        console.log(`👤 Shaxs tanish modali ko'rsatildi: ${personData.full_name}`);
    }

    hidePersonRecognitionModal() {
        const overlay = this.dom.get('personRecognitionOverlay');
        overlay.classList.remove('active');
    }

    showEmotionModal(data) {
        const { person, emotion, emotion_uz, confidence, face_confidence, all_emotions } = data;

        // Create emotion modal if it doesn't exist
        let modal = document.getElementById('emotionModal');
        if (!modal) {
            modal = this.createEmotionModal();
            document.body.appendChild(modal);
        }

        // Get emotion info
        const emotionInfo = EMOTIONS[emotion] || EMOTIONS.neutral;

        // Update modal content
        document.getElementById('emotionModalPersonName').textContent = person.full_name;
        document.getElementById('emotionModalPersonPhoto').src = person.photo_url || '';
        document.getElementById('emotionModalEmotionIcon').textContent = emotionInfo.icon;
        document.getElementById('emotionModalEmotionName').textContent = emotion_uz;
        document.getElementById('emotionModalEmotionConfidence').textContent = `${Math.round(confidence)}%`;
        document.getElementById('emotionModalFaceConfidence').textContent = `${Math.round(face_confidence)}%`;

        // Update emotion container background with dynamic color and animation
        const emotionContainer = document.getElementById('emotionModalEmotionContainer');
        if (emotionContainer) {
            emotionContainer.style.background = emotionInfo.gradient;

            // Update glow animation with emotion color
            const glowKeyframes = `
                @keyframes emotionGlowDynamic {
                    0%, 100% { box-shadow: 0 20px 60px ${emotionInfo.color}66; }
                    50% { box-shadow: 0 20px 80px ${emotionInfo.color}99; }
                }
            `;

            // Add or update keyframes
            let styleSheet = document.getElementById('dynamicEmotionStyles');
            if (!styleSheet) {
                styleSheet = document.createElement('style');
                styleSheet.id = 'dynamicEmotionStyles';
                document.head.appendChild(styleSheet);
            }
            styleSheet.textContent = glowKeyframes;

            // Apply dynamic animation
            emotionContainer.style.animation = 'emotionGlowDynamic 3s ease-in-out infinite';
        }

        // Update person photo border color
        const personPhoto = document.getElementById('emotionModalPersonPhoto');
        if (personPhoto) {
            personPhoto.style.borderColor = emotionInfo.color;
        }

        // Add entrance animation trigger
        setTimeout(() => {
            const modalContent = modal.querySelector('.emotion-modal-large');
            if (modalContent) {
                modalContent.style.animation = 'emotionSlideIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
            }
        }, 10);

        // Show modal
        modal.classList.add('active');
        console.log(`🎭 Emotion modali ko'rsatildi: ${person.full_name} - ${emotion_uz} (${confidence}%)`);
    }

    hideEmotionModal() {
        const modal = document.getElementById('emotionModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    createEmotionModal() {
        const modal = document.createElement('div');
        modal.id = 'emotionModal';
        modal.className = 'modal-overlay';

        // Add styles for animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes emotionPulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }

            @keyframes emotionSlideIn {
                from {
                    opacity: 0;
                    transform: translateY(-50px) scale(0.9);
                }
                to {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            @keyframes emotionGlow {
                0%, 100% { box-shadow: 0 20px 60px rgba(16, 185, 129, 0.4); }
                50% { box-shadow: 0 20px 80px rgba(16, 185, 129, 0.7); }
            }

            @keyframes numberCount {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            #emotionModal {
                z-index: 10000 !important;
            }

            .emotion-modal-large {
                position: fixed !important;
                top: 50% !important;
                left: 50% !important;
                transform: translate(-50%, -50%) !important;
                width: 85vw !important;
                max-width: 700px !important;
                max-height: 85vh !important;
                background: transparent !important;
                border-radius: 25px !important;
                animation: emotionSlideIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
                overflow: visible !important;
                box-shadow: none !important;
                z-index: 10001 !important;
            }

            .emotion-person-photo-large {
                width: 220px !important;
                height: 220px !important;
                border-radius: 50% !important;
                object-fit: cover !important;
                animation: emotionPulse 2s ease-in-out infinite !important;
                box-shadow: 0 15px 50px rgba(0,0,0,0.3) !important;
                border: 5px solid white !important;
            }

            .emotion-name-huge {
                font-size: 72px !important;
                font-weight: 900 !important;
                letter-spacing: 2px !important;
                text-transform: uppercase !important;
                background: linear-gradient(135deg, #fff 0%, rgba(255,255,255,0.8) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                text-shadow: 0 5px 20px rgba(0,0,0,0.2);
            }

            .confidence-card {
                background: rgba(255,255,255,0.15);
                backdrop-filter: blur(10px);
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 20px;
                padding: 30px 45px;
                margin: 15px;
                display: inline-block;
                animation: numberCount 0.8s ease-out;
            }

            .confidence-number {
                font-size: 64px !important;
                font-weight: 900 !important;
                color: white;
                text-shadow: 0 5px 15px rgba(0,0,0,0.3);
            }

            .confidence-label {
                font-size: 18px;
                color: rgba(255,255,255,0.9);
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-top: 10px;
                font-weight: 600;
            }
        `;
        document.head.appendChild(style);

        modal.innerHTML = `
            <div class="emotion-modal-large">
                <div style="text-align: center; padding: 30px 20px;">
                    <!-- Main Content - Centered -->
                    <div>
                        <!-- Emotion Display -->
                        <div id="emotionModalEmotionContainer"
                             style="background: linear-gradient(135deg, #10b981, #059669);
                                    padding: 40px 30px;
                                    border-radius: 30px;
                                    margin: 0 auto;
                                    box-shadow: 0 20px 60px rgba(16, 185, 129, 0.4);
                                    transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
                                    position: relative;
                                    overflow: hidden;
                                    animation: emotionGlow 3s ease-in-out infinite;">

                            <!-- Background decoration -->
                            <div style="position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%); animation: emotionPulse 4s ease-in-out infinite;"></div>

                            <!-- Content -->
                            <div style="position: relative; z-index: 1;">
                                <!-- Person Photo Large -->
                                <img id="emotionModalPersonPhoto" class="emotion-person-photo-large" src="" alt="Person">

                                <!-- Person Name -->
                                <h3 id="emotionModalPersonName" style="font-size: 32px; margin: 20px 0 10px 0; color: white; font-weight: 800;"></h3>

                                <!-- Emotion Name with Icon -->
                                <div style="display: flex; align-items: center; justify-content: center; gap: 20px; margin: 20px 0 40px 0;">
                                    <div id="emotionModalEmotionIcon" style="font-size: 80px;">😊</div>
                                    <div id="emotionModalEmotionName" class="emotion-name-huge" style="color: white;">XURSAND</div>
                                </div>

                                <!-- Confidence Cards -->
                                <div style="display: flex; justify-content: center; gap: 25px; flex-wrap: wrap;">
                                    <div class="confidence-card">
                                        <div class="confidence-number" id="emotionModalEmotionConfidence">95%</div>
                                        <div class="confidence-label">Emotion Ishonchi</div>
                                    </div>
                                    <div class="confidence-card">
                                        <div class="confidence-number" id="emotionModalFaceConfidence">87%</div>
                                        <div class="confidence-label">Yuz Ishonchi</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Buttons - Modern Design -->
                        <div style="display: flex; gap: 15px; justify-content: center; margin-top: 30px; flex-wrap: wrap;">
                            <button id="emotionModalContinueBtn"
                                    style="padding: 18px 45px;
                                           font-size: 20px;
                                           font-weight: 800;
                                           min-width: 220px;
                                           background: linear-gradient(135deg, #10b981, #059669);
                                           color: white;
                                           border: none;
                                           border-radius: 50px;
                                           cursor: pointer;
                                           transition: all 0.3s ease;
                                           box-shadow: 0 10px 30px rgba(16, 185, 129, 0.4);
                                           text-transform: uppercase;
                                           letter-spacing: 1.5px;"
                                    onmouseover="this.style.transform='translateY(-3px) scale(1.05)'; this.style.boxShadow='0 15px 40px rgba(16, 185, 129, 0.6)'"
                                    onmouseout="this.style.transform='translateY(0) scale(1)'; this.style.boxShadow='0 10px 30px rgba(16, 185, 129, 0.4)'">
                                ▶ Davom etish
                            </button>
                            <button id="emotionModalTestBtn"
                                    style="padding: 18px 45px;
                                           font-size: 20px;
                                           font-weight: 800;
                                           min-width: 220px;
                                           background: linear-gradient(135deg, #f59e0b, #d97706);
                                           color: white;
                                           border: none;
                                           border-radius: 50px;
                                           cursor: pointer;
                                           transition: all 0.3s ease;
                                           box-shadow: 0 10px 30px rgba(245, 158, 11, 0.4);
                                           text-transform: uppercase;
                                           letter-spacing: 1.5px;"
                                    onmouseover="this.style.transform='translateY(-3px) scale(1.05)'; this.style.boxShadow='0 15px 40px rgba(245, 158, 11, 0.6)'"
                                    onmouseout="this.style.transform='translateY(0) scale(1)'; this.style.boxShadow='0 10px 30px rgba(245, 158, 11, 0.4)'">
                                📝 Testga yuborish
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        return modal;
    }
}

// ==================== API Service ====================
class APIService {
    static async detectEmotion(imageData) {
        try {
            const response = await fetch(CONFIG.API.DETECT_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData }),
                signal: AbortSignal.timeout(CONFIG.API.TIMEOUT)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return { success: true, data };

        } catch (error) {
            console.error('API Error:', error);
            return {
                success: false,
                error: error.message || 'Network error'
            };
        }
    }

    static async saveEmotion(s, personId = null) {
        try {
            const payload = { s };
            if (personId) {
                payload.person_id = personId;
            }

            const response = await fetch(CONFIG.API.SAVE_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
                signal: AbortSignal.timeout(CONFIG.API.TIMEOUT)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return { success: true, data };

        } catch (error) {
            console.error('Save Error:', error);
            return {
                success: false,
                error: error.message || 'Failed to save'
            };
        }
    }

    static async saveCameraLog(emotionData) {
        try {
            const response = await fetch('/api/save-camera-log/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(emotionData),
                signal: AbortSignal.timeout(CONFIG.API.TIMEOUT)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return { success: true, data };

        } catch (error) {
            console.error('Save CameraLog Error:', error);
            return {
                success: false,
                error: error.message || 'Failed to save camera log'
            };
        }
    }
}

// ==================== Video Processor ====================
class VideoProcessor {
    static captureFrame(imageElement) {
        const canvas = document.createElement('canvas');
        // Use natural dimensions of the image
        canvas.width = imageElement.naturalWidth || imageElement.width || 640;
        canvas.height = imageElement.naturalHeight || imageElement.height || 480;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(imageElement, 0, 0, canvas.width, canvas.height);

        return canvas.toDataURL('image/jpeg', CONFIG.DETECTION.IMAGE_QUALITY);
    }

    static async requestCamera() {
        try {
            // For IP camera, we just need to verify the stream is accessible
            const response = await fetch('/api/camera-config/', {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });

            if (!response.ok) {
                throw new Error('Camera configuration not available');
            }

            const config = await response.json();
            console.log('📷 IP Camera config:', config);

            return { success: true, config };
        } catch (error) {
            console.error('Camera Error:', error);
            return {
                success: false,
                error: error.message || 'IP Camera not accessible'
            };
        }
    }
}

// ==================== Main Application ====================
class EmotionApp {
    constructor() {
        this.state = new AppState();
        this.dom = new DOMManager();
        this.ui = new UIController(this.dom);

        this.init();
    }

    init() {
        this.attachEventListeners();
        this.ui.showCameraOffMessage();  // Show initial "camera off" state
        console.log('✅ Emotion Detection System initialized');
        console.log('📊 Configuration:', CONFIG);
    }

    attachEventListeners() {
        this.dom.get('startBtn').addEventListener('click', () => this.start());
        this.dom.get('stopBtn').addEventListener('click', () => this.stop());

        // Emotion action buttons (in Results card)
        this.dom.get('emotionContinueBtn').addEventListener('click', async () => {
            console.log('🔘 CONTINUE tugmasi bosildi');

            try {
                const personName = this.state.currentPerson?.full_name || 'Shaxs';
                console.log('   📍 Current person:', personName);
                console.log('   📍 isPaused:', this.state.isPaused);
                console.log('   📍 isDetecting:', this.state.isDetecting);

                // Save CameraLog if emotion data exists
                if (this.state.currentEmotionData) {
                    console.log('   💾 CameraLog saqlanmoqda...', this.state.currentEmotionData);

                    try {
                        const result = await APIService.saveCameraLog(this.state.currentEmotionData);

                        if (result.success) {
                            console.log('   ✅ CameraLog muvaffaqiyatli saqlandi:', result.data);
                            this.ui.showToast(`✓ ${personName} - saqlandi`, 'success');
                        } else {
                            console.error('   ❌ CameraLog saqlashda xatolik:', result.error);
                            this.ui.showToast(`⚠️ Saqlashda xatolik: ${result.error}`, 'error');
                        }
                    } catch (saveError) {
                        console.error('   💥 CameraLog API xatolik:', saveError);
                        this.ui.showToast(`⚠️ Serverga ulanishda xatolik`, 'error');
                    }

                    // Clear stored emotion data
                    this.state.currentEmotionData = null;
                    console.log('   🧹 Emotion data tozalandi');
                } else {
                    console.log('   ℹ️ Emotion data yo\'q, faqat davom etish');
                    this.ui.showToast(`✓ ${personName} - davom etilmoqda`, 'success');
                }

                // MUHIM: Davom etish bosilganda HAMMA MA'LUMOTLAR TOZALANADI
                console.log('   🔄 Dashboard tozalanmoqda va keyingi shaxsni qidirish boshlanyapti...');

                // Person state tozalash
                this.state.currentPerson = null;
                this.state.lastPersonId = null;
                this.state.resetPersonHistory();
                this.state.currentEmotionData = null;

                // UI ni tozalash (boshlang'ich holatga qaytarish)
                console.log('   🧹 UI tozalanmoqda...');
                this.resetUIToInitialState();

                // Person card'dagi rasmni aniq tozalash
                this.dom.get('personPhoto').src = '';
                this.dom.get('personPhoto').alt = '';
                this.dom.get('personName').textContent = '---';

                // Emotion ichidagi shaxs ma'lumotlarini ham tozalash
                this.dom.get('emotionPersonPhotoWrapper').style.display = 'none';
                this.dom.get('emotionPersonPhoto').src = '';
                this.dom.get('emotionPersonName').textContent = '';

                // Hide buttons
                this.dom.get('emotionActions').style.display = 'none';

                // Resume detection (yangi shaxsni kutish)
                console.log('   ▶️ Detection davom ettirilmoqda - yangi shaxsni kutish...');
                this.state.resume();

                console.log('   ✅ State after resume:');
                console.log('      - isPaused:', this.state.isPaused);
                console.log('      - isDetecting:', this.state.isDetecting);

                console.log('✅ CONTINUE tugmasi muvaffaqiyatli bajarildi - keyingi shaxsni kutmoqda');

            } catch (error) {
                console.error('💥 CONTINUE tugmasi KRITIK XATOLIK:', error);
                console.error('   Stack:', error.stack);

                // Xatolik bo'lsa ham davom etishga harakat qilish
                try {
                    this.state.currentEmotionData = null;
                    this.state.currentPerson = null;
                    this.state.lastPersonId = null;
                    this.dom.get('emotionActions').style.display = 'none';
                    this.resetUIToInitialState();
                    this.state.resume();

                    this.ui.showToast('⚠️ Xatolik, lekin davom ettirildi', 'warning');
                    console.log('   🔧 Emergency resume bajarildi');
                } catch (recoveryError) {
                    console.error('   💥💥 RECOVERY ham muvaffaqiyatsiz:', recoveryError);
                    this.ui.showToast('❌ Jiddiy xatolik - sahifani yangilang', 'error');
                }
            }
        });

        this.dom.get('emotionTestBtn').addEventListener('click', () => {
            console.log('=== EMOTION TEST BTN CLICKED ===');
            console.log('Current person state:', this.state.currentPerson);
            console.log('Emotion data state:', this.state.currentEmotionData);

            const personId = this.state.currentPerson?.id;
            const personName = this.state.currentPerson?.full_name || 'Shaxs';
            const detectedEmotion = this.state.currentEmotionData?.emotion;

            console.log('Extracted personId:', personId);
            console.log('Extracted personName:', personName);
            console.log('Extracted emotion:', detectedEmotion);

            if (personId) {
                // Testga yunaltirish - aniqlangan emotion bilan yangi sahifaga yo'naltirish
                let testUrl = `/test/${personId}/`;
                if (detectedEmotion) {
                    testUrl += `?emotion=${detectedEmotion}`;
                    console.log(`📝 ${personName} testga yuborilmoqda (${detectedEmotion} aniqlandi)...`);
                } else {
                    console.log(`📝 ${personName} testga yuborilmoqda (barcha savollar)...`);
                }
                console.log('Redirecting to:', testUrl);
                window.location.href = testUrl;
            } else {
                console.error('ERROR: PersonId topilmadi!');
                this.ui.showToast('⚠️ Shaxs tanilmadi', 'error');
            }
        });

        // Results modal event listeners

        // "Tasdiqlash" button - Normal confirmation
        this.dom.get('confirmNormalBtn').addEventListener('click', () => {
            const personName = this.state.currentPerson?.full_name || 'Hodim';
            this.ui.hideResultsModal();
            this.ui.showToast(`✅ ${personName} tasdiqlandi`, 'success');

            // Prepare for next person
            this.prepareForNextPerson();
        });

        // "Testga yuborish" button - Send to testing
        this.dom.get('confirmTestingBtn').addEventListener('click', () => {
            console.log('=== CONFIRM TESTING BTN CLICKED ===');
            console.log('Current person state:', this.state.currentPerson);
            console.log('Emotion data state:', this.state.currentEmotionData);

            const personId = this.state.currentPerson?.id;
            const personName = this.state.currentPerson?.full_name || 'Hodim';
            const detectedEmotion = this.state.currentEmotionData?.emotion;

            console.log('Extracted personId:', personId);
            console.log('Extracted personName:', personName);
            console.log('Extracted emotion:', detectedEmotion);

            if (personId) {
                // Testga yunaltirish
                let testUrl = `/test/${personId}/`;
                if (detectedEmotion) {
                    testUrl += `?emotion=${detectedEmotion}`;
                }
                console.log(`🧪 ${personName} testga yuborilmoqda...`);
                console.log('Redirecting to:', testUrl);
                window.location.href = testUrl;
            } else {
                console.error('ERROR: PersonId topilmadi!');
                this.ui.hideResultsModal();
                this.ui.showToast(`⚠️ Shaxs ma'lumotlari topilmadi`, 'error');
            }
        });

        // Person Recognition Modal "Continue" button
        this.dom.get('continueRecognitionBtn').addEventListener('click', () => {
            this.ui.hidePersonRecognitionModal();

            // Reset UI to initial state before continuing
            this.resetUIToInitialState();

            this.state.resume();  // Resume
            this.ui.showToast(`✓ ${this.state.currentPerson?.full_name || 'Shaxs'} uchun emotion aniqlash boshlandi`, 'success');
            console.log('✓ Shaxs tanildi, emotion aniqlash boshlandi...');

            // Immediately trigger  instead of waiting for next interval
            setTimeout(() => this.detectEmotion(), 500);
        });

        // Person Recognition Modal "Send to Testing" button
        this.dom.get('sendToTestingBtn').addEventListener('click', () => {
            console.log('=== SEND TO TESTING BTN CLICKED ===');
            console.log('Current person state:', this.state.currentPerson);

            const personId = this.state.currentPerson?.id;
            const personName = this.state.currentPerson?.full_name || 'Shaxs';

            console.log('Extracted personId:', personId);
            console.log('Extracted personName:', personName);

            if (personId) {
                // Testga yunaltirish (emotion yig'masdan)
                let testUrl = `/test/${personId}/`;
                console.log(`⚠️ ${personName} testga yuborilmoqda (emotion yig'masdan)...`);
                console.log('Redirecting to:', testUrl);
                window.location.href = testUrl;
            } else {
                console.error('ERROR: PersonId topilmadi!');
                this.ui.hidePersonRecognitionModal();
                this.ui.showToast(`⚠️ Shaxs ma'lumotlari topilmadi`, 'error');
            }
        });

        // Emotion Modal event listeners (will be attached when modal is created)
        document.addEventListener('click', (e) => {
            // Continue button in emotion modal
            if (e.target && e.target.id === 'emotionModalContinueBtn') {
                const personName = this.state.currentPerson?.full_name || 'Shaxs';
                this.ui.hideEmotionModal();

                // Reset UI to initial state
                this.resetUIToInitialState();

                this.state.resume();  // Resume  for next emotion
                this.ui.showToast(`✓ ${personName} - davom etilmoqda`, 'success');
                console.log(`✓ ${personName} - davom etilmoqda`);

                // Trigger next
                setTimeout(() => this.detectEmotion(), 500);
            }

            // Test button in emotion modal
            if (e.target && e.target.id === 'emotionModalTestBtn') {
                const personName = this.state.currentPerson?.full_name || 'Shaxs';
                this.ui.hideEmotionModal();
                this.ui.showToast(`⚠️ ${personName} testga yuborildi`, 'warning');
                console.log(`⚠️ ${personName} testga yuborildi`);

                // Prepare for next person
                this.prepareForNextPerson();
            }
        });
    }

    async start() {
        try {
            // Request camera access (verify IP camera is available)
            const cameraResult = await VideoProcessor.requestCamera();

            if (!cameraResult.success) {
                this.ui.showToast('IP kameraga ulanishda xatolik. Kamera ishlamayapti.', 'error');
                return;
            }

            // Set up IP camera stream - asosiy kamera streamini olish
            const videoElement = this.dom.get('video');
            videoElement.src = cameraResult.config.stream_url || '/api/camera-stream/';
            videoElement.style.display = 'block';

            console.log('📹 Kamera stream yuklandi:', cameraResult.config.camera_id, cameraResult.config.stream_url);

            // Update UI
            this.ui.hideVideoOverlay();
            this.ui.enableControls(false, true);
            this.ui.updateStatus(true);

            // Reset Results card and Person card to initial state
            this.resetUIToInitialState();

            // Start - MUHIM: barcha flaglarni to'g'ri o'rnatish
            this.state.isDetecting = true;
            this.state.isPaused = false;  // ANIQ false qilish
            this.state.waitingForNewPerson = false;
            this.state.currentEmotionData = null;
            this.state.currentPerson = null;
            this.state.lastPersonId = null;
            this.state.startTime = Date.now();
            this.startSessionTimer();
            this.startLoop();

            console.log('✅ Start: isDetecting =', this.state.isDetecting, ', isPaused =', this.state.isPaused);

            this.ui.showToast('IP kamera ishga tushdi', 'success');

        } catch (error) {
            console.error('Start Error:', error);
            this.ui.showToast('Tizimni ishga tushirishda xatolik', 'error');
        }
    }

    resetUIToInitialState() {
        // Reset Results card to initial state
        this.ui.updateEmotion('neutral', 0, false, null);

        // Reset Person card to initial state
        this.ui.updatePersonCard(null);

        console.log('🔄 UI boshlang\'ich holatga keltirildi');
    }

    stop() {
        this.state.reset();

        // Stop IP camera stream
        const videoElement = this.dom.get('video');
        videoElement.src = '';
        videoElement.style.display = 'none';

        this.ui.showVideoOverlay();
        this.ui.enableControls(true, false);
        this.ui.updateStatus(false);
        this.ui.showCameraOffMessage();  // Show camera off message
        this.ui.renderHistory([]);  // Clear history display

        // Reset emotion display to default (Aniqlanmagan)
        this.ui.updateEmotion('neutral', 0, false, null);
        this.ui.updateStats(0, '00:00');

        // MUHIM: Shaxs ma'lumotlarini ham tozalash
        this.ui.updatePersonCard(null);

        // Emotion ichidagi shaxs ma'lumotlarini ham tozalash
        this.dom.get('emotionPersonPhotoWrapper').style.display = 'none';
        this.dom.get('emotionPersonPhoto').src = '';
        this.dom.get('emotionPersonName').textContent = '';

        // Hide emotion action buttons
        this.dom.get('emotionActions').style.display = 'none';

        console.log('🛑 To\'xtatildi - BARCHA ma\'lumotlar (emotion + shaxs) tozalandi');
        this.ui.showToast('Sessiya to\'xtatildi', 'info');
    }

    prepareForNextPerson() {
        console.log('🔄 Keyingi hodim uchun tayyorlanmoqda...');

        // Reset person-specific state
        this.state.currentPerson = null;
        this.state.lastPersonId = null;
        this.state.resetPersonHistory();
        this.state.clearBuffer();

        // Reset UI displays
        this.ui.updatePersonCard(null);  // Show "no person" message
        this.ui.renderHistory([]);  // Clear history

        // Keep camera running and  active
        console.log('✅ Keyingi hodim kutilmoqda...');
    }

    startSessionTimer() {
        this.state.timeInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.state.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            const timeString = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            this.ui.updateStats(this.state.scanCount, timeString);
        }, 1000);
    }

    startLoop() {
        // First detection immediately
        setTimeout(() => this.detectEmotion(), 1000);

        // Then periodic detection
        this.state.detectionInterval = setInterval(
            () => this.detectEmotion(),
            CONFIG.DETECTION.INTERVAL
        );
    }

    async detectEmotion() {
        // Skip detection if not running
        if (!this.state.isDetecting) {
            return;
        }

        // Agar PAUSED va emotion data MAVJUD bo'lsa - to'xtatish
        // Lekin agar PAUSED va emotion YO'Q bo'lsa - davom etish (emotion olish uchun)
        if (this.state.isPaused && this.state.currentEmotionData) {
            return; // To'liq pause - emotion allaqachon topilgan
        }

        // Prevent concurrent calls
        if (this._isProcessing) {
            console.log('⏭️ Detection allaqachon ishlamoqda, skip');
            return;
        }

        this._isProcessing = true;
        console.log('🔍 Detection boshlandi...');

        try {
            this.ui.showLoading();

            // Capture video frame
            const imageData = VideoProcessor.captureFrame(this.dom.get('video'));
            if (!imageData) {
                console.warn('⚠️ Video frame olish mumkin emas');
                return;
            }

            // Send to API
            const result = await APIService.detectEmotion(imageData);

            if (!result.success) {
                throw new Error(result.error);
            }

            const { data } = result;

            // PERSON DETECTION
            if (data.person && !this.state.isPaused) {
                const newPersonId = data.person.id;
                const isNewPerson = (this.state.lastPersonId !== newPersonId) || this.state.waitingForNewPerson;

                if (isNewPerson) {
                    console.log('🔄 Yangi shaxs tanildi:', data.person.full_name);
                    this.state.lastPersonId = newPersonId;
                    this.state.waitingForNewPerson = false;
                    this.state.resetPersonHistory();
                    this.ui.renderHistory([], data.person.full_name);
                }

                // HAR DOIM shaxs ma'lumotlarini ko'rsatish va saqlash
                this.state.currentPerson = data.person;
                this.ui.updatePersonCard(data.person);
                console.log('✅ Shaxs dashboarda ko\'rsatildi:', data.person.full_name);

                // MUHIM: HAR DOIM PAUSE - ma'lumotlar DOIM saqlanadi
                console.log('⏸️ PAUSE - ma\'lumotlar "Davom etish" bosilmaguncha saqlanadi');
                this.state.pause();
            }
            // Pause holatida person data HECH QACHON o'zgartirilmaydi!

            // Process emotion result (shaxs tanilganda to'xtatadi)
            if (data.emotion && data.emotion !== 'aniqlanmadi' && data.emotion_uz) {
                console.log('🎭 Emotion ma\'lumoti:', {
                    emotion: data.emotion,
                    emotion_uz: data.emotion_uz,
                    confidence: data.emotion_confidence
                });

                // Use emotion key directly from backend (English)
                const emotionKey = data.emotion;
                const emotionConfidence = data.emotion_confidence || 0;

                console.log('🔍 DEBUG - Pause shartlari:');
                console.log('   emotionKey =', emotionKey);
                console.log('   currentPerson =', this.state.currentPerson);
                console.log('   isPaused =', this.state.isPaused);

                // Show emotion in Results card if person is recognized
                if (emotionKey && this.state.currentPerson) {
                    // Store emotion data for saving when user clicks Continue
                    this.state.currentEmotionData = {
                        person_id: this.state.currentPerson.id,
                        emotion: emotionKey,
                        emotion_uz: data.emotion_uz,
                        emotion_confidence: emotionConfidence
                    };

                    // Update Results card with emotion data, person photo, and show action buttons
                    this.ui.updateEmotion(emotionKey, emotionConfidence, true, this.state.currentPerson);

                    // Add to history
                    this.addToHistory(emotionKey, emotionConfidence);

                    console.log(`🎭 ${this.state.currentPerson.full_name}: ${data.emotion_uz} (${emotionConfidence}%)`);
                    console.log('✅ Emotion dashboarda ko\'rsatildi');
                    console.log('⏸️ PAUSED - "Davom etish" bosguningizcha ma\'lumotlar saqlanadi');

                    // Increment scan count
                    this.state.scanCount++;

                } else if (emotionKey && !this.state.currentPerson) {
                    // Emotion detected but no person recognized
                    console.log('⚠️ Emotion aniqlandi lekin shaxs tanilmadi');
                    this.ui.updateEmotion(emotionKey, emotionConfidence, false, null);
                }
            } else if (data.error) {
                console.warn('⚠️ Backend warning:', data.error);
            }

        } catch (error) {
            console.error('💥 detectEmotion xatolik:', error);
            console.error('   Stack:', error.stack);
            // Faqat birinchi xatolikda toast ko'rsatish (spam bo'lmasligi uchun)
            if (!this._lastErrorTime || Date.now() - this._lastErrorTime > 5000) {
                this.ui.showToast('⚠️ Aniqlashda xatolik', 'error');
                this._lastErrorTime = Date.now();
            }
        } finally {
            this.ui.hideLoading();
            this._isProcessing = false;
        }
    }

    findEmotionKey(uzbekName) {
        return Object.keys(EMOTIONS).find(
            key => EMOTIONS[key].uz === uzbekName
        );
    }

    addToHistory(emotion, confidence) {
        const now = new Date();
        const time = now.toLocaleTimeString('uz-UZ', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        const emotionData = EMOTIONS[emotion];

        const historyItem = {
            emotion,
            emotionData,
            confidence: Math.round(confidence),
            time,
            timestamp: now.getTime()
        };

        // Add to general history (for backward compatibility)
        this.state.history.unshift(historyItem);
        if (this.state.history.length > CONFIG.UI.HISTORY_MAX_ITEMS) {
            this.state.history.pop();
        }

        // If person is detected, add to person-specific history
        if (this.state.currentPerson) {
            this.state.personHistory.unshift(historyItem);

            // Keep only last 5 items for person (matching buffer size)
            if (this.state.personHistory.length > CONFIG.DETECTION.REQUIRED_SAMPLES) {
                this.state.personHistory.pop();
            }

            // Render person-specific history
            this.ui.renderHistory(this.state.personHistory, this.state.currentPerson.name);
        } else {
            // No person detected, render general history
            this.ui.renderHistory(this.state.history);
        }
    }

    getSessionTime() {
        if (!this.state.startTime) return '00:00';

        const elapsed = Math.floor((Date.now() - this.state.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;

        return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    async saveToDatabase() {
        try {
            console.log('💾 Saving 5 samples to database...');

            const samples = this.state.getSamplesForSave();
            const personId = this.state.currentPerson ? this.state.currentPerson.id : null;

            // Send to save API
            const result = await APIService.saveEmotion(samples, personId);

            if (result.success) {
                const { data } = result;

                let message = `✅ ${data.emotion_uzbek} bazaga saqlandi (${data.occurrence_count}/5)`;
                if (data.person_name) {
                    message = `✅ ${data.person_name}: ${data.emotion_uzbek} saqlandi (${data.occurrence_count}/5)`;
                }

                this.ui.showToast(message, 'success');

                // Clear buffer after successful save
                this.state.clearBuffer();

                // Update person emotion count if person exists
                if (this.state.currentPerson && data.person_name) {
                    this.state.currentPerson.camera_logs_count++;
                    this.ui.updatePersonCard(this.state.currentPerson);
                }

                // Always show results modal after saving (regardless of testing requirement)
                if (this.state.currentPerson && data.emotion_analysis) {
                    console.log('📊 5 ta emotion to\'plandi! Natijalar modalini ko\'rsatish...');

                    // Wait a moment before showing modal
                    setTimeout(() => {
                        this.ui.showResultsModal(
                            this.state.currentPerson,
                            data.emotion_analysis,
                            data.requires_testing
                        );
                    }, 500);
                } else {
                    console.log('⚠️ Shaxs ma\'lumotlari yo\'q, modal ko\'rsatilmaydi');
                }

                console.log('✅ Successfully saved to database:', data);
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            console.error('💥 Save to database error:', error);

            // Check if error is about max records limit
            if (error.message && error.message.includes('5 ta yozuv')) {
                this.ui.showToast(`⚠️ Bu shaxs uchun maksimal yozuvlar to'ldi`, 'warning');
            } else {
                this.ui.showToast('❌ Bazaga saqlashda xatolik', 'error');
            }
        }
    }
}

// ==================== Camera Management ====================
// Kamera slotlarini boshqarish
const cameraSlots = {
    slot1: null,
    slot2: null,
    slot3: null,
    slot4: null
};

// Global funksiya - window obyektiga biriktirish
window.loadCameras = async function() {
    console.log('🔄 loadCameras() chaqirildi...');
    try {
        const timestamp = new Date().getTime();
        const url = `/api/cameras/?t=${timestamp}`;
        console.log('📡 API ga so\'rov:', url);

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        console.log('📥 Response olindi:', response.status);

        const data = await response.json();
        console.log('📦 Data:', data);

        if (data.success && data.cameras) {
            console.log(`✅ ${data.total} ta kamera topildi`);
            renderCameraMenu(data.cameras);
        } else {
            console.error('❌ Kameralarni yuklashda xatolik:', data.error);
            const menuList = document.getElementById('cameraMenuList');
            if (menuList) {
                menuList.innerHTML = `<p style="padding: 1rem; text-align: center; color: var(--danger);">❌ Xatolik</p>`;
            }
        }
    } catch (error) {
        console.error('💥 Kameralarni yuklashda xatolik:', error);
        const menuList = document.getElementById('cameraMenuList');
        if (menuList) {
            menuList.innerHTML = `<p style="padding: 1rem; text-align: center; color: var(--danger);">❌ Xatolik: ${error.message}</p>`;
        }
    }
}

// Chap menyuni yaratish
function renderCameraMenu(cameras) {
    const menuList = document.getElementById('cameraMenuList');
    if (!menuList) {
        console.error('❌ cameraMenuList topilmadi!');
        return;
    }

    console.log('📹 renderCameraMenu chaqirildi, kameralar:', cameras.length);

    if (!cameras || cameras.length === 0) {
        menuList.innerHTML = '<p style="padding: 1rem; text-align: center; color: var(--text-secondary);">Kameralar yo\'q</p>';
        return;
    }

    let menuHTML = '';
    cameras.forEach(camera => {
        menuHTML += `
            <div class="camera-menu-item" data-camera-id="${camera.id}" onclick="showCameraInSlot(${camera.id}, '${camera.name}', '${camera.stream_url}')">
                <div class="camera-menu-item-icon">📹</div>
                <div class="camera-menu-item-info">
                    <div class="camera-menu-item-name">${camera.name}</div>
                    <div class="camera-menu-item-status ${camera.is_active ? 'online' : ''}">${camera.is_active ? '🟢 Online' : '🔴 Offline'}</div>
                </div>
            </div>
        `;
    });

    menuList.innerHTML = menuHTML;
    console.log(`✅ ${cameras.length} ta kamera menyuda ko'rsatildi`);

    // AVTOMATIK YUKLASH O'CHIRILDI - faqat bosganida ochiladi
    console.log('ℹ️ Kameralarni ochish uchun kamera nomini bosing');
}

// Kamerani birinchi bo'sh slotga qo'yish
window.showCameraInSlot = function(cameraId, cameraName, streamUrl) {
    console.log(`📹 Kamera ko'rsatilmoqda: ${cameraName} (ID: ${cameraId})`);

    // MUHIM: cemera_app stream ishlatish - yuzda ramka va emotion bilan!
    const emotionStreamUrl = `/cemera/stream/${cameraId}/`;
    console.log(`   🎭 Emotion stream URL: ${emotionStreamUrl}`);

    // Birinchi bo'sh slotni topish
    let targetSlot = null;
    for (let i = 1; i <= 4; i++) {
        const slotKey = `slot${i}`;
        if (!cameraSlots[slotKey]) {
            targetSlot = slotKey;
            break;
        }
    }

    if (!targetSlot) {
        // Barcha slotlar to'liq - birinchisini almashtirish
        targetSlot = 'slot1';
        console.log('⚠️ Barcha slotlar to\'liq - slot1 almashtirilmoqda');
    }

    // Slotni to'ldirish (emotion stream bilan)
    cameraSlots[targetSlot] = { id: cameraId, name: cameraName, url: emotionStreamUrl };
    renderCameraSlot(targetSlot, cameraId, cameraName, emotionStreamUrl);

    console.log(`✅ Kamera ${cameraName} - ${targetSlot} ga qo'yildi (emotion stream)`);
}

// Slotda kamerani ko'rsatish - YAXSHILANGAN
function renderCameraSlot(slotKey, cameraId, cameraName, streamUrl) {
    const slotNumber = slotKey.replace('slot', '');
    const slotElement = document.getElementById(`cameraSlot${slotNumber}`);

    if (!slotElement) {
        console.error(`❌ cameraSlot${slotNumber} topilmadi!`);
        return;
    }

    slotElement.classList.add('active');

    // Loading state
    slotElement.innerHTML = `
        <div class="camera-slot-content">
            <div class="camera-slot-header">
                <span class="camera-slot-name">📹 ${cameraName}</span>
                <span class="camera-status loading">⏳ Yuklanmoqda...</span>
                <div class="camera-slot-buttons">
                    <button class="camera-slot-expand" onclick="toggleCameraFullscreen('${slotKey}')" title="Kattalashtirish">
                        <span class="expand-icon">&lt;&gt;</span>
                    </button>
                    <button class="camera-slot-close" onclick="closeCameraSlot('${slotKey}')" title="Yopish">×</button>
                </div>
            </div>
            <div class="camera-loading">
                <div class="spinner"></div>
                <p>Kamera ulanmoqda...</p>
            </div>
            <img id="camImg${slotNumber}" src="${streamUrl}?t=${Date.now()}"
                 class="camera-slot-video" alt="${cameraName}" style="display:none;">
        </div>
    `;

    // Image load handlers
    const img = document.getElementById(`camImg${slotNumber}`);
    const statusEl = slotElement.querySelector('.camera-status');
    const loadingEl = slotElement.querySelector('.camera-loading');

    img.onload = function() {
        console.log(`✅ Kamera ${cameraName} yuklandi`);
        img.style.display = 'block';
        if (loadingEl) loadingEl.style.display = 'none';
        if (statusEl) {
            statusEl.textContent = '✅ Ishlayapti';
            statusEl.className = 'camera-status success';
        }
    };

    img.onerror = function() {
        console.error(`❌ Kamera ${cameraName} xatolik`);
        if (loadingEl) {
            loadingEl.innerHTML = '<p style="color:#ff4444;">❌ Ulanmadi</p>';
        }
        if (statusEl) {
            statusEl.textContent = '❌ Xato';
            statusEl.className = 'camera-status error';
        }
        // Retry after 3 seconds
        setTimeout(() => {
            console.log(`🔄 Qayta urinish: ${cameraName}`);
            img.src = `${streamUrl}?t=${Date.now()}`;
        }, 3000);
    };

    // Timeout after 10 seconds
    setTimeout(() => {
        if (img.style.display === 'none') {
            console.warn(`⏱️ Timeout: ${cameraName}`);
            if (statusEl) {
                statusEl.textContent = '⏱️ Timeout';
                statusEl.className = 'camera-status error';
            }
        }
    }, 10000);
}

// Slotdan kamerani o'chirish
window.closeCameraSlot = function(slotKey) {
    console.log(`🔴 Slot yopilmoqda: ${slotKey}`);

    cameraSlots[slotKey] = null;

    const slotNumber = slotKey.replace('slot', '');
    const slotElement = document.getElementById(`cameraSlot${slotNumber}`);

    if (slotElement) {
        slotElement.classList.remove('active');
        slotElement.innerHTML = `
            <div class="camera-slot-empty">
                <span class="slot-icon">📹</span>
                <span class="slot-text">Kamera ${slotNumber}</span>
            </div>
        `;
    }

    console.log(`✅ ${slotKey} tozalandi`);
}

// Kamerani kattalashtirish/kichiklashtirish (fullscreen toggle)
window.toggleCameraFullscreen = function(slotKey) {
    const slotNumber = slotKey.replace('slot', '');
    const slotElement = document.getElementById(`cameraSlot${slotNumber}`);

    if (!slotElement) {
        console.error(`❌ cameraSlot${slotNumber} topilmadi!`);
        return;
    }

    const isFullscreen = slotElement.classList.contains('fullscreen');
    const expandIcon = slotElement.querySelector('.expand-icon');

    if (isFullscreen) {
        // Kichiklashtirish - joyiga qaytarish
        slotElement.classList.remove('fullscreen');
        if (expandIcon) {
            expandIcon.innerHTML = '&lt;&gt;';  // < > belgisi
        }
        console.log(`📐 ${slotKey} odatiy o'lchamga qaytarildi`);
    } else {
        // Kattalashtirish - to'liq ekran
        slotElement.classList.add('fullscreen');
        if (expandIcon) {
            expandIcon.innerHTML = '&gt;&lt;';  // > < belgisi
        }
        console.log(`📺 ${slotKey} kattalashtrildi (fullscreen)`);
    }
}

// ESC tugmasi bilan fullscreen dan chiqish
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        // Barcha fullscreen kameralarni topish
        const fullscreenSlots = document.querySelectorAll('.camera-slot.fullscreen');
        fullscreenSlots.forEach(slot => {
            const slotId = slot.id;  // cameraSlot1, cameraSlot2, etc.
            const slotNumber = slotId.replace('cameraSlot', '');
            const slotKey = `slot${slotNumber}`;
            toggleCameraFullscreen(slotKey);
        });
    }
});

// Eski renderCameras funksiyasini yangilab qo'yamiz (backward compatibility uchun)
window.renderCameras = function(cameras) {
    renderCameraMenu(cameras);
}

// ==================== BACKGROUND WORKER CONTROLS ====================

// Flag to track if workers have been auto-started
let workersAutoStarted = false;

// AVTOMATIK: Background workers ni bir marta ishga tushirish (UI tugmasiz)
window.autoStartBackgroundWorkers = async function() {
    // Agar allaqachon ishga tushirilgan bo'lsa, skip
    if (workersAutoStarted) {
        console.log('⏭️ Background workers allaqachon ishga tushirilgan');
        return;
    }

    console.log('🚀 Background workers avtomatik ishga tushirilmoqda...');

    try {
        const response = await fetch('/cemera/start-workers/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.success) {
            workersAutoStarted = true;
            console.log(`✅ Background workers avtomatik ishga tushdi: ${data.loaded_cameras} ta kamera`);

            if (window.emotionApp && window.emotionApp.ui) {
                window.emotionApp.ui.showToast(`✅ ${data.loaded_cameras} ta kamera ishga tushdi`, 'success');
            }
        } else {
            console.error('❌ Background workers ishga tushmadi:', data.error);
        }
    } catch (error) {
        console.error('💥 Background workers xatolik:', error);
    }
}

// Background workers ni ishga tushirish (manual, agar kerak bo'lsa)
window.startBackgroundWorkers = async function() {
    console.log('🚀 Background workers ishga tushirilmoqda...');

    const startBtn = document.getElementById('startWorkersBtn');
    const stopBtn = document.getElementById('stopWorkersBtn');
    const statusText = document.getElementById('workerStatusText');
    const statusDot = document.getElementById('workerStatusDot');

    startBtn.disabled = true;
    startBtn.textContent = '⏳ Ishga tushirilmoqda...';

    try {
        const response = await fetch('/cemera/start-workers/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.success) {
            console.log('✅ Background workers ishga tushdi:', data.message);

            // UI ni yangilash
            statusText.textContent = `Background Workers: ${data.loaded_cameras} ta kamera ishlayapti`;
            statusDot.classList.add('active');

            startBtn.style.display = 'none';
            stopBtn.style.display = 'block';

            // Success toast
            if (window.emotionApp && window.emotionApp.ui) {
                window.emotionApp.ui.showToast(`✅ ${data.loaded_cameras} ta kamera ishga tushdi`, 'success');
            }

            // Kameralarni qayta yuklash
            loadCameras();
        } else {
            console.error('❌ Xatolik:', data.error);
            statusText.textContent = `Xatolik: ${data.error}`;

            if (window.emotionApp && window.emotionApp.ui) {
                window.emotionApp.ui.showToast(`❌ Xatolik: ${data.error}`, 'error');
            }

            startBtn.disabled = false;
            startBtn.textContent = '🚀 Barcha Kameralarni Ishga Tushirish';
        }
    } catch (error) {
        console.error('💥 Network error:', error);
        statusText.textContent = 'Xatolik: Serverga ulanishda muammo';

        if (window.emotionApp && window.emotionApp.ui) {
            window.emotionApp.ui.showToast('❌ Serverga ulanishda xatolik', 'error');
        }

        startBtn.disabled = false;
        startBtn.textContent = '🚀 Barcha Kameralarni Ishga Tushirish';
    }
}

// Background workers ni to'xtatish
window.stopBackgroundWorkers = async function() {
    console.log('🔴 Background workers to\'xtatilmoqda...');

    const startBtn = document.getElementById('startWorkersBtn');
    const stopBtn = document.getElementById('stopWorkersBtn');
    const statusText = document.getElementById('workerStatusText');
    const statusDot = document.getElementById('workerStatusDot');

    stopBtn.disabled = true;
    stopBtn.textContent = '⏳ To\'xtatilmoqda...';

    try {
        const response = await fetch('/cemera/stop-workers/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.success) {
            console.log('✅ Background workers to\'xtatildi');

            // UI ni yangilash
            statusText.textContent = 'Background Workers: To\'xtatilgan';
            statusDot.classList.remove('active');

            startBtn.style.display = 'block';
            stopBtn.style.display = 'none';

            if (window.emotionApp && window.emotionApp.ui) {
                window.emotionApp.ui.showToast('✓ Background workers to\'xtatildi', 'info');
            }
        } else {
            console.error('❌ Xatolik:', data.error);

            if (window.emotionApp && window.emotionApp.ui) {
                window.emotionApp.ui.showToast(`❌ Xatolik: ${data.error}`, 'error');
            }

            stopBtn.disabled = false;
            stopBtn.textContent = '⏹️ Barcha Kameralarni To\'xtatish';
        }
    } catch (error) {
        console.error('💥 Network error:', error);

        if (window.emotionApp && window.emotionApp.ui) {
            window.emotionApp.ui.showToast('❌ Serverga ulanishda xatolik', 'error');
        }

        stopBtn.disabled = false;
        stopBtn.textContent = '⏹️ Barcha Kameralarni To\'xtatish';
    }
}

// Worker status ni tekshirish
window.checkWorkerStatus = async function() {
    try {
        const response = await fetch('/cemera/worker-status/');
        const data = await response.json();

        const statusText = document.getElementById('workerStatusText');
        const statusDot = document.getElementById('workerStatusDot');
        const startBtn = document.getElementById('startWorkersBtn');
        const stopBtn = document.getElementById('stopWorkersBtn');

        if (data.success && data.running && data.active_threads > 0) {
            // Workers ishlamoqda
            statusText.textContent = `Background Workers: ${data.active_threads} ta kamera ishlayapti`;
            statusDot.classList.add('active');
            startBtn.style.display = 'none';
            stopBtn.style.display = 'block';
            console.log(`✅ Worker status: ${data.active_threads} ta kamera ishlayapti`);
        } else {
            // Workers to'xtatilgan
            statusText.textContent = 'Background Workers: To\'xtatilgan';
            statusDot.classList.remove('active');
            startBtn.style.display = 'block';
            stopBtn.style.display = 'none';
            console.log('⏹️ Worker status: To\'xtatilgan');
        }
    } catch (error) {
        console.error('⚠️ Worker status tekshirishda xatolik:', error);
    }
}

// ==================== Application Entry Point ====================
document.addEventListener('DOMContentLoaded', () => {
    try {
        window.emotionApp = new EmotionApp();
        console.log('🎬 Application ready');
    } catch (error) {
        console.error('❌ Application initialization failed:', error);
    }
});

// ==================== Error Handling ====================
window.addEventListener('error', (event) => {
    console.error('Global Error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled Promise Rejection:', event.reason);
});
