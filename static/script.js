document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const messagesContainer = document.getElementById('messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    const ttsCheckbox = document.getElementById('tts-checkbox');
    
    // Accessibility Controls
    const fontSizeBtns = document.querySelectorAll('.font-size-btn');
    const themeBtns = document.querySelectorAll('.theme-btn');
    const contrastBtns = document.querySelectorAll('.contrast-btn');
    const normalVersionBtn = document.querySelector('.normal-version-btn');
    const accessibilityPanel = document.querySelector('.accessibility-panel');
    
    // Load saved preferences
    loadPreferences();
    
    // Event Listeners
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Mic button functionality
    micBtn.addEventListener('click', startSpeechRecognition);
    
    // Audio playback for bot messages
    document.addEventListener('click', function(e) {
        if (e.target.closest('.play-audio-btn')) {
            const messageContent = e.target.closest('.message').querySelector('.message-content p').textContent;
            speakText(messageContent);
        }
    });
    
    // Font size controls
    fontSizeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const size = this.classList.contains('small') ? 'small' : 
                          this.classList.contains('medium') ? 'medium' : 'large';
            
            document.body.classList.remove('font-small', 'font-medium', 'font-large');
            document.body.classList.add('font-' + size);
            
            // Update active state
            fontSizeBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            savePreferences();
        });
    });
    
    // Theme controls
    themeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const theme = this.classList.contains('light-theme') ? 'light' : 
                           this.classList.contains('dark-theme') ? 'dark' : 
                           this.classList.contains('blue-theme') ? 'blue' : 'yellow';
            
            document.body.classList.remove('light-theme', 'dark-theme', 'blue-theme', 'yellow-theme');
            if (theme !== 'light') {
                document.body.classList.add(theme + '-theme');
            }
            
            // Update active state
            themeBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            savePreferences();
        });
    });
    
    // Contrast controls
    contrastBtns.forEach((btn, index) => {
        btn.addEventListener('click', function() {
            const highContrastEnabled = index === 1; // Second button is "Включить"
            
            if (highContrastEnabled) {
                document.body.classList.add('high-contrast');
            } else {
                document.body.classList.remove('high-contrast');
            }
            
            // Update active state
            contrastBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            savePreferences();
        });
    });
    
    // Normal version button
    normalVersionBtn.addEventListener('click', function() {
        resetToDefaults();
    });
    
    // Add accessibility toggle button
    const accessibilityToggle = document.createElement('button');
    accessibilityToggle.className = 'accessibility-toggle';
    accessibilityToggle.innerHTML = '<i class="fa-solid fa-universal-access"></i>';
    accessibilityToggle.setAttribute('aria-label', 'Настройки доступности');
    accessibilityToggle.style.position = 'fixed';
    accessibilityToggle.style.top = '10px';
    accessibilityToggle.style.right = '10px';
    accessibilityToggle.style.zIndex = '1000';
    accessibilityToggle.style.padding = '0.5rem';
    accessibilityToggle.style.backgroundColor = '#0092cf';
    accessibilityToggle.style.color = 'white';
    accessibilityToggle.style.border = 'none';
    accessibilityToggle.style.borderRadius = '50%';
    accessibilityToggle.style.width = '40px';
    accessibilityToggle.style.height = '40px';
    accessibilityToggle.style.display = 'flex';
    accessibilityToggle.style.justifyContent = 'center';
    accessibilityToggle.style.alignItems = 'center';
    accessibilityToggle.style.fontSize = '1.5rem';
    accessibilityToggle.style.cursor = 'pointer';
    accessibilityToggle.style.boxShadow = '0 2px 5px rgba(0, 0, 0, 0.2)';
    accessibilityToggle.style.display = 'none'; // Initially hidden
    
    document.body.appendChild(accessibilityToggle);
    
    // Toggle accessibility panel
    let panelVisible = true; // Panel is visible by default
    
    accessibilityToggle.addEventListener('click', function() {
        panelVisible = !panelVisible;
        document.querySelector('.accessibility-wrapper').style.display = panelVisible ? 'flex' : 'none';
        accessibilityToggle.style.display = panelVisible ? 'none' : 'flex';
        
        // Save panel state
        localStorage.setItem('accessibilityPanelVisible', panelVisible.toString());
    });
    
    // Close button for accessibility panel
    const closeBtn = document.querySelector('.close-panel-btn');
    
    closeBtn.addEventListener('click', function() {
        document.querySelector('.accessibility-wrapper').style.display = 'none';
        accessibilityToggle.style.display = 'flex';
        panelVisible = false;
        
        // Save panel state
        localStorage.setItem('accessibilityPanelVisible', 'false');
    });
    
    // Check if panel should be hidden on load
    const savedPanelState = localStorage.getItem('accessibilityPanelVisible');
    if (savedPanelState === 'false') {
        document.querySelector('.accessibility-wrapper').style.display = 'none';
        accessibilityToggle.style.display = 'flex';
        panelVisible = false;
    }
    
    // Functions
    function sendMessage() {
        const message = userInput.value.trim();
        if (message === '') return;
        
        // Add user message to chat
        addMessage(message, 'user');
        
        // Clear input
        userInput.value = '';
        
        // Send the message to the server
        fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: message }),
        })
        .then(response => response.json())
        .then(data => {
            addMessage(data.answer, 'bot');
            
            // Auto speak bot response if enabled
            if (ttsCheckbox.checked) {
                speakText(data.answer);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addMessage("Произошла ошибка при обработке вашего запроса.", 'bot');
        });
    }
    
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const paragraph = document.createElement('p');
        paragraph.textContent = text;
        
        messageContent.appendChild(paragraph);
        messageDiv.appendChild(messageContent);
        
        // Add play button for bot messages
        if (sender === 'bot') {
            const playButton = document.createElement('button');
            playButton.className = 'play-audio-btn';
            playButton.setAttribute('aria-label', 'Прослушать сообщение');
            
            const icon = document.createElement('i');
            icon.className = 'fa-solid fa-volume-high';
            
            playButton.appendChild(icon);
            messageDiv.appendChild(playButton);
        }
        
        messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    function startSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window)) {
            alert('Ваш браузер не поддерживает распознавание речи. Попробуйте Google Chrome.');
            return;
        }
        
        const recognition = new webkitSpeechRecognition();
        recognition.lang = 'ru-RU';
        recognition.interimResults = false;
        
        micBtn.classList.add('recording');
        micBtn.innerHTML = '<i class="fa-solid fa-stop"></i>';
        
        recognition.start();
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
        };
        
        recognition.onend = function() {
            micBtn.classList.remove('recording');
            micBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error', event.error);
            micBtn.classList.remove('recording');
            micBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        };
    }
    
    function speakText(text) {
        if (!('speechSynthesis' in window)) {
            alert('Ваш браузер не поддерживает синтез речи. Попробуйте Google Chrome.');
            return;
        }
        
        // Stop any current speech
        window.speechSynthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'ru-RU';
        
        // Get Russian voice if available
        const voices = speechSynthesis.getVoices();
        const russianVoice = voices.find(voice => voice.lang.includes('ru'));
        if (russianVoice) {
            utterance.voice = russianVoice;
        }
        
        window.speechSynthesis.speak(utterance);
    }
    
    function savePreferences() {
        const preferences = {
            fontSize: document.body.classList.contains('font-large') ? 'large' : 
                      document.body.classList.contains('font-small') ? 'small' : 'medium',
            theme: document.body.classList.contains('dark-theme') ? 'dark' : 
                   document.body.classList.contains('blue-theme') ? 'blue' : 
                   document.body.classList.contains('yellow-theme') ? 'yellow' : 'light',
            highContrast: document.body.classList.contains('high-contrast'),
            ttsEnabled: ttsCheckbox.checked,
            panelVisible: panelVisible
        };
        
        localStorage.setItem('chatAssistantPreferences', JSON.stringify(preferences));
    }
    
    function loadPreferences() {
        const savedPrefs = localStorage.getItem('chatAssistantPreferences');
        if (!savedPrefs) return;
        
        const preferences = JSON.parse(savedPrefs);
        
        // Apply font size
        document.body.classList.add('font-' + preferences.fontSize);
        fontSizeBtns.forEach(btn => {
            btn.classList.remove('active');
            if ((preferences.fontSize === 'small' && btn.classList.contains('small')) ||
                (preferences.fontSize === 'medium' && btn.classList.contains('medium')) ||
                (preferences.fontSize === 'large' && btn.classList.contains('large'))) {
                btn.classList.add('active');
            }
        });
        
        // Apply theme
        if (preferences.theme !== 'light') {
            document.body.classList.add(preferences.theme + '-theme');
        }
        themeBtns.forEach(btn => {
            btn.classList.remove('active');
            if ((preferences.theme === 'light' && btn.classList.contains('light-theme')) ||
                (preferences.theme === 'dark' && btn.classList.contains('dark-theme')) ||
                (preferences.theme === 'blue' && btn.classList.contains('blue-theme')) ||
                (preferences.theme === 'yellow' && btn.classList.contains('yellow-theme'))) {
                btn.classList.add('active');
            }
        });
        
        // Apply contrast
        if (preferences.highContrast) {
            document.body.classList.add('high-contrast');
            contrastBtns[1].classList.add('active');
            contrastBtns[0].classList.remove('active');
        } else {
            document.body.classList.remove('high-contrast');
            contrastBtns[0].classList.add('active');
            contrastBtns[1].classList.remove('active');
        }
        
        // Apply TTS setting
        ttsCheckbox.checked = preferences.ttsEnabled;
        
        // Apply panel visibility
        if (preferences.panelVisible === false) {
            document.querySelector('.accessibility-wrapper').style.display = 'none';
            accessibilityToggle.style.display = 'flex';
            panelVisible = false;
        }
    }
    
    function resetToDefaults() {
        document.body.classList.remove('font-small', 'font-medium', 'font-large');
        document.body.classList.remove('dark-theme', 'blue-theme', 'yellow-theme');
        document.body.classList.remove('high-contrast');
        
        document.body.classList.add('font-medium');
        
        fontSizeBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.classList.contains('medium')) {
                btn.classList.add('active');
            }
        });
        
        themeBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.classList.contains('light-theme')) {
                btn.classList.add('active');
            }
        });
        
        contrastBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent === 'Выключить') {
                btn.classList.add('active');
            }
        });
        
        ttsCheckbox.checked = false;
        
        // Show accessibility panel
        document.querySelector('.accessibility-wrapper').style.display = 'flex';
        accessibilityToggle.style.display = 'none';
        panelVisible = true;
        
        localStorage.removeItem('chatAssistantPreferences');
        localStorage.removeItem('accessibilityPanelVisible');
    }
    
    // Initialize voices for speechSynthesis (needed for some browsers)
    if ('speechSynthesis' in window) {
        speechSynthesis.onvoiceschanged = function() {
            speechSynthesis.getVoices();
        };
    }
    
    // Apply initial classes based on saved preferences
    document.body.classList.add('font-medium'); // Default
    
    // Fix active class initialization for font buttons
    fontSizeBtns.forEach(btn => {
        if (btn.classList.contains('medium')) {
            btn.classList.add('active');
        }
    });
});