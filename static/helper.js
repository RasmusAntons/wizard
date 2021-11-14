let levelCache = {};

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
        }
        return res.json();
    });
}

function levelBlockToObj(levelBlock) {
    const level = {
        id: Number(levelBlock.getElementsByClassName('level_id')[0].textContent),
        name: levelBlock.getElementsByClassName('level_name')[0].value,
        grid_location: [null, null]
    };
    for (let solutionType of ['solutions', 'unlocks']) {
        const solutionsStr = levelBlock.getElementsByClassName(`level_${solutionType}`)[0].value;
        level[solutionType] = solutionsStr.split('\n').filter(e => e);
    }
    for (let discordIdType of ['discord_channel', 'discord_role', 'extra_discord_role']) {
        level[discordIdType] = levelBlock.getElementsByClassName(`level_${discordIdType}`)[0].value || null;
    }
    return level;
}

function createLevelBlock(level) {
    const levelDiv = document.createElement('div');
    let setEditedStatus = () => {
        const oldLevel = levelCache[level.id];
        const newLevel = levelBlockToObj(levelDiv);
        let changed = false;
        for (let key of Object.getOwnPropertyNames(newLevel)) {
            if (JSON.stringify(oldLevel[key]) !== JSON.stringify(newLevel[key])) {
                changed = true;
                break;
            }
        }
        levelDiv.classList.toggle('changed', changed);
    };
    levelDiv.className = 'level_block';
    const levelIdElem = document.createElement('span');
    levelIdElem.className = 'level_id';
    levelIdElem.style.color = 'grey';
    levelIdElem.textContent = level.id;
    levelDiv.appendChild(levelIdElem);
    const titleSeparator = document.createElement('span');
    titleSeparator.textContent = ' '
    levelDiv.appendChild(titleSeparator);
    const levelNameElem = document.createElement('input');
    levelNameElem.className = 'level_name';
    levelNameElem.oninput = setEditedStatus;
    levelNameElem.value = level.name;
    levelDiv.appendChild(levelNameElem);
    levelDiv.appendChild(document.createElement('br'));
    for (let solutionType of ['solutions', 'unlocks']) {
        const solutionLabel = document.createElement('label');
        solutionLabel.for = `${level.id}_${solutionType}`;
        solutionLabel.textContent = `${solutionType}:`;
        levelDiv.appendChild(solutionLabel);
        const solutionElem = document.createElement('textarea');
        solutionElem.className = `level_${solutionType}`;
        solutionElem.oninput = setEditedStatus;
        solutionElem.id = solutionLabel.for;
        solutionElem.value = level[solutionType].join('\n');
        levelDiv.appendChild(solutionElem);
        levelDiv.appendChild(document.createElement('br'));
    }
    for (let discordIdType of ['discord_channel', 'discord_role', 'extra_discord_role']) {
        const discordIdLabel = document.createElement('label');
        discordIdLabel.for = `${level.id}_${discordIdType}`;
        discordIdLabel.textContent = `${discordIdType}:`;
        levelDiv.appendChild(discordIdLabel);
        const discordIdElem = document.createElement('input');
        discordIdElem.className = `level_${discordIdType}`;
        discordIdElem.oninput = setEditedStatus;
        discordIdElem.maxLength = 18;
        discordIdElem.id = discordIdLabel.for;
        discordIdElem.value = level[discordIdType] || '';
        levelDiv.appendChild(discordIdElem);
        const discordIdCreateButton = document.createElement('button');
        discordIdCreateButton.textContent = 'create';
        discordIdCreateButton.onclick = () => {
            const channelName = prompt('Channel name');
            if (channelName === undefined)
                return;
            const apiPath = (discordIdType === 'discord_channel') ? '/api/channels/' : '/api/roles/';
            apiCall(apiPath, 'POST', {'name': channelName}).then(r => {
                discordIdElem.value = r.id;
                setEditedStatus();
            });
        };
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
            editButton.onclick = () =>
                apiCall('/api/config/', 'POST', {[key]: prompt('value')}).then(loadConfig);
            p.appendChild(editButton);
            const deleteButton = document.createElement('button');
            deleteButton.textContent = 'delete';
            deleteButton.onclick = () => apiCall(`/api/config/${key}`, 'DELETE').then(loadConfig);
            p.appendChild(deleteButton);
            optionsElem.appendChild(p);
        }
    });
}

function loadLevels() {
    apiCall('/api/levels/').then(levels => {
        levelCache = levels;
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
    document.getElementById('add_level_button').onclick = () =>
        apiCall('/api/levels/', 'POST').then(createLevelBlock);
    document.getElementById('save_levels_button').onclick = () => {
        for (let levelBlock of document.querySelectorAll('.level_block.changed')) {
            const newLevel = levelBlockToObj(levelBlock);
            apiCall(`/api/levels/${newLevel.id}`, 'POST', newLevel).then(r => {
                if (r.message === 'ok') {
                    levelBlock.classList.toggle('changed', false);
                    levelCache[newLevel.id] = newLevel;
                } else {
                    levelBlock.classList.toggle('error', true);
                }
            });
            console.log(newLevel);
        }
    }
});
