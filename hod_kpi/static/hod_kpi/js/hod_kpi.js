// Interactive JS logic for HOD KPI Dashboard

document.addEventListener('DOMContentLoaded', () => {
    // --- 1. Tab Switching for Production View ---
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;
            
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.style.display = 'none');
            
            button.classList.add('active');
            const targetContent = document.getElementById(`production-${targetTab}`);
            if (targetContent) {
                targetContent.style.display = 'block';
            }
        });
    });

    // --- 2. Auto-save Deviation Form Fields (AJAX on blur) ---
    const feedbackInputs = document.querySelectorAll('.kpi-feedback-input');
    feedbackInputs.forEach(input => {
        input.addEventListener('blur', () => {
            const recordId = input.dataset.recordId;
            const field = input.dataset.field;
            const value = input.value;
            
            saveKPIFeedback(recordId, field, value, input);
        });
    });

    function saveKPIFeedback(recordId, field, value, element) {
        const url = "/hod-kpi/save/kpi-feedback/";
        const originalBorder = element.style.borderColor;
        element.style.borderColor = 'var(--jspl-blue)';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                record_id: recordId,
                field: field,
                value: value
            })
        })
        .then(response => {
            if (response.ok) {
                element.style.borderColor = 'var(--status-green)';
                setTimeout(() => { element.style.borderColor = ''; }, 1000);
                showToast("Feedback auto-saved.");
            } else {
                element.style.borderColor = 'var(--status-red)';
                showToast("Failed to save feedback.", "error");
            }
        })
        .catch(err => {
            element.style.borderColor = 'var(--status-red)';
            showToast("Connection error while saving.", "error");
            console.error("Save error:", err);
        });
    }

    // --- 3. Auto-save Delay Explanation Fields (AJAX on blur) ---
    const delayInputs = document.querySelectorAll('.delay-explanation-input');
    delayInputs.forEach(input => {
        input.addEventListener('blur', () => {
            const delayId = input.dataset.delayId;
            const value = input.value;
            
            saveDelayExplanation(delayId, value, input);
        });
    });

    function saveDelayExplanation(delayId, value, element) {
        const url = "/hod-kpi/save/delay-explanation/";
        element.style.borderColor = 'var(--jspl-blue)';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                delay_id: delayId,
                explanation: value
            })
        })
        .then(response => {
            if (response.ok) {
                element.style.borderColor = 'var(--status-green)';
                setTimeout(() => { element.style.borderColor = ''; }, 1000);
                showToast("Explanation auto-saved.");
            } else {
                element.style.borderColor = 'var(--status-red)';
            }
        })
        .catch(err => {
            element.style.borderColor = 'var(--status-red)';
            console.error("Save error:", err);
        });
    }

    // --- 4. Auto-save Monthly Submission Summary (AJAX on blur) ---
    const monthlyInputs = document.querySelectorAll('.monthly-input');
    monthlyInputs.forEach(input => {
        input.addEventListener('blur', () => {
            const submissionId = input.dataset.submissionId;
            const field = input.dataset.field;
            const value = input.value;
            
            saveMonthlyInput(submissionId, field, value, input);
        });
    });

    function saveMonthlyInput(submissionId, field, value, element) {
        const url = "/hod-kpi/save/monthly-inputs/";
        element.style.borderColor = 'var(--jspl-blue)';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                submission_id: submissionId,
                field: field,
                value: value
            })
        })
        .then(response => {
            if (response.ok) {
                element.style.borderColor = 'var(--status-green)';
                setTimeout(() => { element.style.borderColor = ''; }, 1000);
                showToast("Summary inputs auto-saved.");
            } else {
                element.style.borderColor = 'var(--status-red)';
            }
        })
        .catch(err => {
            element.style.borderColor = 'var(--status-red)';
            console.error("Save error:", err);
        });
    }

    // --- 5. Generate AI Insights Interface Handler ---
    const aiBtn = document.getElementById('generate-ai-btn');
    if (aiBtn) {
        aiBtn.addEventListener('click', () => {
            const submissionId = aiBtn.dataset.submissionId;
            const insightsContainer = document.getElementById('ai-insights-content');
            const skeleton = document.getElementById('ai-insights-skeleton');
            
            insightsContainer.style.display = 'none';
            skeleton.style.display = 'flex';
            aiBtn.disabled = true;
            aiBtn.innerText = "Analyzing...";

            fetch("/hod-kpi/ai-insights/", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    submission_id: submissionId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('ai-summary-text').innerText = data.summary;
                    
                    const recList = document.getElementById('ai-recommendations-list');
                    recList.innerHTML = '';
                    
                    data.recommendations.forEach(rec => {
                        const li = document.createElement('div');
                        li.className = 'ai-recommendation-item';
                        li.innerHTML = `
                            <span class="ai-icon-bullet">💡</span>
                            <span style="font-size: 0.85rem; color: var(--jspl-text);">${rec}</span>
                        `;
                        recList.appendChild(li);
                    });
                    
                    showToast("AI insights generated successfully!");
                } else {
                    showToast("Failed to generate AI insights.", "error");
                }
            })
            .catch(err => {
                showToast("Error communicating with AI service.", "error");
                console.error("AI error:", err);
            })
            .finally(() => {
                skeleton.style.display = 'none';
                insightsContainer.style.display = 'block';
                aiBtn.disabled = false;
                aiBtn.innerText = "Refresh AI Insights";
            });
        });
    }

    // --- Utility: Get CSRF Token from Cookie ---
    function getCSRFToken() {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, 10) === 'csrftoken=') {
                    cookieValue = decodeURIComponent(cookie.substring(10));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // --- Utility: Show Toast Notifications ---
    function showToast(message, type = "success") {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.style.background = type === 'success' ? 'var(--jspl-navy)' : 'var(--status-red)';
        toast.style.color = '#fff';
        toast.style.padding = '12px 24px';
        toast.style.borderRadius = '8px';
        toast.style.boxShadow = 'var(--shadow-md)';
        toast.style.fontSize = '0.85rem';
        toast.style.fontWeight = '600';
        toast.style.marginTop = '10px';
        toast.style.transition = 'opacity 0.3s ease';
        toast.style.opacity = '0';
        toast.innerText = message;
        
        container.appendChild(toast);
        setTimeout(() => { toast.style.opacity = '1'; }, 10);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => { toast.remove(); }, 300);
        }, 3000);
    }
});
