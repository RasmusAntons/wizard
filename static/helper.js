let levelsOriginal = {};
let levelsChanged = {};
let levelBlocks = {};
let selectedLevelId;
let snapDistance = 20;
const unsetValues = [null, undefined, ""];

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

function compareLevels(levelA, levelB) {
    for (let key of Object.getOwnPropertyNames(levelA)) {
        if (JSON.stringify(levelA[key]) !== JSON.stringify(levelB[key])) {
            if (unsetValues.includes(levelA[key]) && unsetValues.includes(levelB[key])) {
                continue;
            }
            return true;
        }
    }
    return false;
}

function cloneLevel(level) {
    return JSON.parse(JSON.stringify(level));
}

function createLevelBlock(level) {
    levelsOriginal[level.id] = level;
    levelsChanged[level.id] = cloneLevel(level);
    const levelBlock = document.createElement("div");
    levelBlocks[level.id] = levelBlock;
    levelBlock.className = 'block';
    const levelName = document.createElement("p");
    levelName.textContent = level.name;
    levelBlock.appendChild(levelName);
    document.getElementById('background').appendChild(levelBlock);
    const markersDiv = document.createElement("div");
    markersDiv.className = "markers-div";
    levelBlock.appendChild(markersDiv);
    for (let markerType of ['solutions', 'inactive_solutions', 'discord_channel', 'inactive_discord_channel',
        'discord_role', 'inactive_discord_role', 'unlocks', 'inactive_unlocks', 'extra_discord_role',
        'inactive_extra_discord_role', 'edited']) {
        const markerDiv = document.createElement('div');
        markerDiv.className = 'tooltip';
        const markerImg = document.createElement('img');
        markerImg.classList.add('marker');
        markerImg.classList.add(`marker_${markerType}`);
        markerImg.src = `/static/marker_${markerType}.svg`;
        markerDiv.appendChild(markerImg);
        const markerTooltip = document.createElement('span');
        markerTooltip.className = 'tooltiptext';
        markerTooltip.textContent = markerType.replaceAll('_', ' ')
            .replace('inactive', 'no');
        markerDiv.appendChild(markerTooltip);
        markersDiv.appendChild(markerDiv);
    }

    let checkForChange = () => {
        levelBlock.classList.toggle('edited', compareLevels(levelsOriginal[level.id], levelsChanged[level.id]));
    };
    let checkForMakers = () => {
        for (let solutionType of ['solutions', 'unlocks'])
            levelBlock.classList.toggle(`has_${solutionType}`, levelsChanged[level.id][solutionType].length > 0);
        for (let discordIdType of ['discord_channel', 'discord_role', 'extra_discord_role'])
            levelBlock.classList.toggle(`has_${discordIdType}`, !unsetValues.includes(levelsChanged[level.id][discordIdType]));
    }
    checkForMakers();

    levelBlock.onmousedown = e => {
        e.stopPropagation();
        selectedLevelId = level.id;
        for (let selectedLevel of document.querySelectorAll('.selected'))
            selectedLevel.classList.toggle('selected', false);
        levelBlock.classList.toggle('selected', true);
        document.getElementById('toolbar-level').style.display = 'block';
        document.getElementById('toolbar-category').style.display = '';
        document.getElementById('toolbar-configurations').style.display = '';

        const levelNameInput = document.getElementById('level_name');
        levelNameInput.value = levelsChanged[level.id].name;
        levelNameInput.oninput = levelNameInput.onchange = () => {
            levelsChanged[level.id].name = levelNameInput.value;
            levelName.textContent = levelsChanged[level.id].name;
            checkForChange();
            checkForMakers();
        };

        for (let solutionType of ['solutions', 'unlocks']) {
            const solutionsInput = document.getElementById(`level_${solutionType}`);
            solutionsInput.value = levelsChanged[level.id][solutionType].join('\n');
            solutionsInput.oninput = solutionsInput.onchange = () => {
                levelsChanged[level.id][solutionType] = solutionsInput.value.split('\n').filter(e => e);
                checkForChange();
                checkForMakers()
            };
        }

        for (let discordIdType of ['discord_channel', 'discord_role', 'extra_discord_role']) {
            const discordIdInput = document.getElementById(`level_${discordIdType}`);
            discordIdInput.value = levelsChanged[level.id][discordIdType];
            discordIdInput.oninput = discordIdInput.onchange = () => {
                levelsChanged[level.id][discordIdType] = discordIdInput.value;
                checkForChange();
                checkForMakers()
            }
        }
    };

    const container = document.getElementById('container');
    const draggable = new PlainDraggable(levelBlock);
    if (level.grid_location[0] !== null)
        draggable.left = level.grid_location[0] - container.scrollLeft;
    if (level.grid_location[1] !== null)
        draggable.top = level.grid_location[1] - container.scrollTop;
    draggable.onDrag = function (position) {
        const snappedX = Math.round((container.scrollLeft + position.left) / snapDistance) * snapDistance - container.scrollLeft;
        const snappedY = Math.round((container.scrollTop + position.top) / snapDistance) * snapDistance - container.scrollTop;
        position.snapped = snappedX !== position.left || snappedY !== position.top;
        if (position.snapped) {
            position.left = snappedX;
            position.top = snappedY;
        }
    };
    draggable.onDragEnd = function (position) {
        levelsChanged[level.id].grid_location = [position.left + container.scrollLeft, position.top + container.scrollTop];
        checkForChange();
    }
    draggable.autoScroll = {target: container};
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
        for (const [id, level] of Object.entries(levels)) {
            createLevelBlock(level);
        }
    });
}

document.addEventListener('DOMContentLoaded', e => {
    if (localStorage.getItem('key') === null) {
        promptKey();
    }
    //loadConfig();
    loadLevels();
    document.getElementById('add_level_button').onclick = () =>
        apiCall('/api/levels/', 'POST').then(createLevelBlock);
    document.getElementById('save_levels_button').onclick = () => {
        for (let [levelId, levelOriginal] of Object.entries(levelsOriginal)) {
            const levelChanged = levelsChanged[levelId];
            const levelBlock = levelBlocks[levelId];
            if (compareLevels(levelOriginal, levelChanged)) {
                apiCall(`/api/levels/${levelId}`, 'POST', levelChanged).then(r => {
                    if (r.message === 'ok') {
                        levelsOriginal[levelChanged.id] = cloneLevel(levelChanged);
                        levelBlock.classList.toggle('edited', false);
                    } else {
                        levelBlock.classList.toggle('error', true);
                    }
                });
            }
        }
    }
    document.getElementById('category-menu-button').onclick = () => {
        document.getElementById('toolbar-level').style.display = '';
        document.getElementById('toolbar-configurations').style.display = '';
        document.getElementById('toolbar-category').style.display = 'block';
    };
    document.getElementById('configuration-menu-button').onclick = () => {
        document.getElementById('toolbar-level').style.display = '';
        document.getElementById('toolbar-category').style.display = '';
        document.getElementById('toolbar-configurations').style.display = 'block';
    };
    const enableGrid = document.getElementById('enable_grid');
    enableGrid.onchange = e => {
        document.getElementById('main').style.fill = e.target.checked ? 'url(#bigGrid)' : '#1a1a21';
    };
    enableGrid.onchange({target: enableGrid});
    for (let [buttonId, inputId, targetKey] of [
            ['level_create_channel', 'level_discord_channel', 'discord_channel'],
            ['level_create_role', 'level_discord_role', 'discord_role'],
            ['level_create_extra_role', 'level_extra_discord_role', 'discord_extra_role']
        ]) {
        const buttonElem = document.getElementById(buttonId);
        const inputElem = document.getElementById(inputId);
        buttonElem.onclick = () => {
            const targetLevelId = selectedLevelId;
            const channelName = prompt('Channel name');
            if (channelName === null)
                return;
            const apiPath = (buttonId === 'level_create_channel') ? '/api/channels/' : '/api/roles/';
            apiCall(apiPath, 'POST', {'name': channelName}).then(r => {
                levelsChanged[targetLevelId][targetKey] = r.id;
                if (selectedLevelId === targetLevelId)
                    inputElem.value = r.id;
                levelBlocks[targetLevelId].classList.toggle('edited', true);
            });
        };
    }
    document.getElementById('background').onmousedown = e => {
        selectedLevelId = undefined;
        document.getElementById('toolbar-level').style.display = '';
        document.getElementById('toolbar-category').style.display = '';
        document.getElementById('toolbar-configurations').style.display = '';
        for (let selectedLevel of document.querySelectorAll('.selected'))
            selectedLevel.classList.toggle('selected', false);
    };
});
