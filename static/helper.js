function promptKey() {
    localStorage.setItem('key', prompt('key'));
}

function apiCall(path, method, data) {
    const key = localStorage.getItem('key');
    const url = new URL(path, document.location.origin);
    url.search = new URLSearchParams({'key': key}).toString();
    const options = {};
    if (method !== undefined)
        options.method = method;
    if (data !== undefined)
        options.body = JSON.stringify(data);
    return fetch(url, options).then(res => {
        if (res.status === 403) {
            promptKey();
            return apiCall(path, method, data);
        } else if (res.status === 204) {
            return true;
        }
        return res.json();
    });
}

function createLevelBlock(level) {
    const levelDiv = document.createElement('div');
    levelDiv.className = 'level_block';
    const levelIdElem = document.createElement('span');
    levelIdElem.style.color = 'grey';
    levelIdElem.textContent = level.id;
    levelDiv.appendChild(levelIdElem);
    const titleSeparator = document.createElement('span');
    titleSeparator.textContent = ' '
    levelDiv.appendChild(titleSeparator);
    const levelNameElem = document.createElement('input');
    levelNameElem.value = level.name;
    levelDiv.appendChild(levelNameElem);
    levelDiv.appendChild(document.createElement('br'));
    for (let solutionType of ['solutions', 'unlocks']) {
        const solutionLabel = document.createElement('label');
        solutionLabel.for = `${level.id}_${solutionType}`;
        solutionLabel.textContent = `${solutionType}:`;
        levelDiv.appendChild(solutionLabel);
        const solutionElem = document.createElement('textarea');
        solutionElem.id = solutionLabel.for;
        solutionElem.value = level[solutionType].join('\n');
        levelDiv.appendChild(solutionElem);
        levelDiv.appendChild(document.createElement('br'));
    }
    for (let discordIdType of ['channel_id', 'role_id', 'extra_role_id']) {
        const discordIdLabel = document.createElement('label');
        discordIdLabel.for = `${level.id}_${discordIdType}`;
        discordIdLabel.textContent = `${discordIdType}:`;
        levelDiv.appendChild(discordIdLabel);
        const discordIdElem = document.createElement('input');
        discordIdElem.maxLength = 18;
        discordIdElem.id = discordIdLabel.for;
        discordIdElem.value = level[discordIdType] || '';
        levelDiv.appendChild(discordIdElem);
        const discordIdCreateButton = document.createElement('button');
        discordIdCreateButton.textContent = 'create';
        discordIdCreateButton.onclick = e => {};
        levelDiv.appendChild(discordIdCreateButton);
        levelDiv.appendChild(document.createElement('br'));
    }
    document.getElementById('levels').appendChild(levelDiv);
}

function loadConfig() {
    const optionsElem = document.getElementById('config');
    while (optionsElem.firstChild)
        optionsElem.removeChild(optionsElem.firstChild);
    apiCall('/api/config/').then(config => {
        for (const [key, value] of Object.entries(config)) {
            const p = document.createElement('p');
            p.textContent = `${key}: ${value}`;
            const editButton = document.createElement('button');
            editButton.textContent = 'edit';
            editButton.onclick = e =>
                apiCall('/api/config/', 'POST', {[key]: prompt('value')}).then(loadConfig);
            p.appendChild(editButton);
            const deleteButton = document.createElement('button');
            deleteButton.textContent = 'delete';
            deleteButton.onclick = e => apiCall(`/api/config/${key}`, 'DELETE').then(loadConfig);
            p.appendChild(deleteButton);
            optionsElem.appendChild(p);
        }
    });
}

function loadLevels() {
    apiCall('/api/levels/').then(levels => {
        for (const [id, level] of Object.entries(levels)) {
            createLevelBlock(level);
        }
    });
}


document.addEventListener('DOMContentLoaded', e => {
    if (localStorage.getItem('key') === null) {
        promptKey();
    }
    loadConfig();
    loadLevels();
    document.getElementById('add_config_button').onclick = e => {
        const configKey = prompt('key');
        if (!configKey)
            return;
        const configValue = prompt('key');
        if (!configValue)
            return;
        apiCall('/api/config/', 'POST', {[configKey]: configValue}).then(loadConfig);
    };
    document.getElementById('add_level_button').onclick = e =>
        apiCall('/api/levels/', 'POST').then(createLevelBlock);
});
