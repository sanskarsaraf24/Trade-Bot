/**
 * Claude Legal Skill Tester - Client Logic
 */

let currentSkill = {
    name: '',
    description: '',
    instructions: '',
    metadata: null
};

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const skillMetadata = document.getElementById('skill-metadata');
const skillNameEl = document.getElementById('skill-name');
const skillDescEl = document.getElementById('skill-desc');
const changeSkillBtn = document.getElementById('change-skill');
const generateBtn = document.getElementById('generate-btn');
const userPrompt = document.getElementById('user-prompt');
const apiKeyInput = document.getElementById('api-key');
const modelSelect = document.getElementById('model-select');
const outputSection = document.getElementById('output-section');
const outputMarkdown = document.getElementById('output-markdown');
const wordCountEl = document.getElementById('word-count');
const downloadDocxBtn = document.getElementById('download-docx');
const resetOutputBtn = document.getElementById('reset-output');

// --- Initialization ---

// Event Listeners
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
});

changeSkillBtn.addEventListener('click', () => {
    skillMetadata.classList.add('hidden');
    dropZone.classList.remove('hidden');
    currentSkill = { name: '', description: '', instructions: '' };
    validateForm();
});

generateBtn.addEventListener('click', generateDraft);
userPrompt.addEventListener('input', validateForm);
apiKeyInput.addEventListener('input', validateForm);

resetOutputBtn.addEventListener('click', () => {
    outputSection.classList.add('hidden');
    outputMarkdown.innerHTML = '';
});

downloadDocxBtn.addEventListener('click', exportToDocx);

// --- File Handling ---

async function handleFiles(files) {
    if (!files.length) return;
    const file = files[0];

    try {
        if (file.name.endsWith('.md')) {
            const content = await file.text();
            parseSkillMd(content);
        } else if (file.name.endsWith('.zip')) {
            const zip = await JSZip.loadAsync(file);
            const skillMdFile = zip.file('SKILL.md');
            if (!skillMdFile) {
                alert('No SKILL.md found in the zip archive.');
                return;
            }
            const content = await skillMdFile.async('text');
            parseSkillMd(content);
        } else {
            alert('Please upload a .md file or a .zip archive.');
            return;
        }

        // Update UI
        dropZone.classList.add('hidden');
        skillMetadata.classList.remove('hidden');
        skillNameEl.textContent = currentSkill.name || 'Unnamed Skill';
        skillDescEl.textContent = currentSkill.description || 'No description provided';
        
        validateForm();
    } catch (err) {
        console.error('Error parsing skill:', err);
        alert('Failed to parse the skill file.');
    }
}

function parseSkillMd(content) {
    const parts = content.split('---');
    if (parts.length >= 3) {
        // Has frontmatter
        try {
            const yaml = jsyaml.load(parts[1]);
            currentSkill.name = yaml.name;
            currentSkill.description = yaml.description;
            currentSkill.metadata = yaml;
            currentSkill.instructions = parts.slice(2).join('---').trim();
        } catch (e) {
            console.warn('Invalid YAML frontmatter, using raw content');
            currentSkill.instructions = content;
        }
    } else {
        currentSkill.instructions = content;
    }
}

function validateForm() {
    const hasSkill = !!currentSkill.instructions;
    const hasPrompt = !!userPrompt.value.trim();
    const hasKey = !!apiKeyInput.value.trim();
    
    generateBtn.disabled = !(hasSkill && hasPrompt && hasKey);
}

// --- API Communication ---

async function generateDraft() {
    const apiKey = apiKeyInput.value.trim();
    const prompt = userPrompt.value.trim();
    const model = modelSelect.value;
    
    // UI Loading state
    generateBtn.disabled = true;
    generateBtn.querySelector('.btn-label').textContent = 'Generating...';
    generateBtn.querySelector('.spinner').classList.remove('hidden');

    try {
        const fullPrompt = `Task: Generate a legal draft based on the following skill instructions and user request.
Constraint: Maximum 1500 words. Format clearly with headings.

SKILL INSTRUCTIONS:
${currentSkill.instructions}

USER REQUEST:
${prompt}`;

        const response = await fetch('http://localhost:8008/api/claude', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                apiKey,
                model,
                messages: [{ role: 'user', content: fullPrompt }],
                system: `You are an expert legal drafting assistant specialized in ${currentSkill.name || 'legal documents'}. ${currentSkill.description || ''}`
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || 'API Request failed');
        }

        const data = await response.json();
        const resultText = data.content[0].text;

        // Render result
        outputSection.classList.remove('hidden');
        outputMarkdown.innerHTML = marked.parse(resultText);
        
        // Word count
        const words = resultText.trim().split(/\s+/).length;
        wordCountEl.textContent = `${words} words`;
        
        // Scroll to output
        outputSection.scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
        console.error('Generation failed:', err);
        alert('Err: ' + err.message);
    } finally {
        generateBtn.disabled = false;
        generateBtn.querySelector('.btn-label').textContent = 'Generate Draft';
        generateBtn.querySelector('.spinner').classList.add('hidden');
        validateForm();
    }
}

// --- .docx Export ---

async function exportToDocx() {
    const text = outputMarkdown.innerText;
    const { Document, Packer, Paragraph, TextRun, HeadingLevel } = docx;

    // Very basic parsing of the rendered text for docx
    // In a production app, we would use a more robust md-to-docx converter
    const lines = text.split('\n').filter(l => l.trim() !== '');
    
    const children = lines.map(line => {
        return new Paragraph({
            children: [new TextRun(line)],
            spacing: { after: 200 }
        });
    });

    const doc = new Document({
        sections: [{
            properties: {},
            children: [
                new Paragraph({
                    text: currentSkill.name || "Legal Draft",
                    heading: HeadingLevel.HEADING_1,
                }),
                ...children
            ],
        }],
    });

    const blob = await Packer.toBlob(doc);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(currentSkill.name || 'Legal_Draft').replace(/\s+/g, '_')}.docx`;
    a.click();
    URL.revokeObjectURL(url);
}
