let levelCache = {};
let gridState = true;
let snapDistance = 20;

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
        name: levelBlock.getElementsByClassName('level_name')[0].value || null,
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
    levelCache[level.id] = level;
    const block = document.createElement("div");
    let setEditedStatus = () => {
        const oldLevel = levelCache[level.id];
        const newLevel = levelBlockToObj(block);
        let edited = false;
        for (let key of Object.getOwnPropertyNames(newLevel)) {
            if (JSON.stringify(oldLevel[key]) !== JSON.stringify(newLevel[key])) {
                edited = true;
                break;
            }
        }
        block.classList.toggle('edited', edited);
    };

    const levelId = document.createElement("span");
    const levelName = document.createElement("input");
    const levelSolutions = document.createElement("textarea");
    const levelUnlocks = document.createElement("textarea");
    const levelChannel = document.createElement("input");
    const levelRole = document.createElement("input");
    const levelBonusRole = document.createElement("input");

    const channelIdCreateButton = document.createElement("button");
    const roleIdCreateButton = document.createElement("button");
    const extraRoleIdCreateButton = document.createElement("button");

    levelName.placeholder = "level name";
    levelSolutions.placeholder = "level solutions";
    levelUnlocks.placeholder = "level unlocks";
    levelChannel.placeholder = "level channel";
    levelRole.placeholder = "level role";
    levelBonusRole.placeholder = "level bonus role";

    channelIdCreateButton.textContent = "create channel";
    roleIdCreateButton.textContent = "create role";
    extraRoleIdCreateButton.textContent = "create extra role";

    levelId.className = "level_id";
    levelName.className = "level_name";
    levelSolutions.className = "level_solutions";
    levelUnlocks.className = "level_unlocks";
    levelChannel.className = "level_discord_channel";
    levelRole.className = "level_discord_role";
    levelBonusRole.className = "level_extra_discord_role";

    levelId.textContent = level.id;
    levelName.value = level.name;
    levelSolutions.value = level.solutions.join('\n');
    levelUnlocks.value = level.unlocks.join('\n');
    levelChannel.value = level.discord_channel;
    levelRole.value = level.discord_role;
    levelBonusRole.value = level.extra_discord_role;

    for (let elem of [levelId, levelName, levelSolutions, levelUnlocks, levelChannel, levelRole, levelBonusRole]) {
        elem.addEventListener("mousedown", e => e.stopPropagation());
        elem.oninput = setEditedStatus;
    }

    for (let [button, inputElem] of [[channelIdCreateButton, levelChannel], [roleIdCreateButton, levelRole], [extraRoleIdCreateButton, levelBonusRole]]) {
        button.onclick = () => {
            const channelName = prompt('Channel name');
            if (channelName === undefined)
                return;
            const apiPath = (button === channelIdCreateButton) ? '/api/channels/' : '/api/roles/';
            apiCall(apiPath, 'POST', {'name': channelName}).then(r => {
                inputElem.value = r.id;
                setEditedStatus();
            });
        };
    }

    block.className = 'block';
    block.appendChild(levelId);
    block.appendChild(levelName);
    block.appendChild(levelSolutions);
    block.appendChild(levelChannel);
    block.appendChild(channelIdCreateButton);
    block.appendChild(levelRole);
    block.appendChild(roleIdCreateButton);
    block.appendChild(levelUnlocks);
    block.appendChild(extraRoleIdCreateButton);
    block.appendChild(levelBonusRole);
    background.appendChild(block);

    const draggable = new PlainDraggable(block);
	draggable.onDrag = function(position) {
	    const snappedX = Math.round((container.scrollLeft + position.left) / snapDistance) * snapDistance - container.scrollLeft;
	    const snappedY = Math.round((container.scrollTop + position.top) / snapDistance) * snapDistance - container.scrollTop;
	    position.snapped = snappedX != position.left || snappedY != position.top;
	    if (position.snapped) {
	        position.left = snappedX;
	        position.top = snappedY;
	    }
    };
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

function toggleGrid() {
     if (gridState) {
        main.style.fill = "#1a1a21";
        gridState = false;
     } else {
        main.style.fill = "url(#bigGrid)";
        gridState = true;
     }
}

document.addEventListener('DOMContentLoaded', e => {
    if (localStorage.getItem('key') === null) {
        promptKey();
    }
    //loadConfig();
    loadLevels();
//    document.getElementById('add_config_button').onclick = e => {
//        const configKey = prompt('key');
//        if (!configKey)
//            return;
//        const configValue = prompt('key');
//        if (!configValue)
//            return;
//        apiCall('/api/config/', 'POST', {[configKey]: configValue}).then(loadConfig);
//    };
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
