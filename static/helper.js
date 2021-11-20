let levelsOriginal = {};
let levelsCurrent = {};
let levelsChanged = {};
let levelBlocks = {};
let categoriesOriginal = {};
let categoriesCurrent = {};
let categoriesChanged = {};
let levelCategoryListItems = {};
let selectedLevelId;
let snapDistance = 20;
const unsetValues = [null, undefined, ""];

function promptKey() {
    localStorage.setItem('key', prompt('key'));
}

// https://stackoverflow.com/a/2117523
function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
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

function cloneObject(obj) {
    return JSON.parse(JSON.stringify(obj));
}

let checkLevelChange = (level_id) => {
    const isChanged = compareLevels(levelsOriginal[level_id], levelsCurrent[level_id]);
    levelBlocks[level_id].classList.toggle('edited', isChanged);
    if (isChanged)
        levelsChanged[level_id] = levelsCurrent[level_id];
    else
        delete levelsChanged[level_id];
};

function createLevelBlock(level, unsaved) {
    levelsOriginal[level.id] = level;
    levelsCurrent[level.id] = cloneObject(level);
    const levelBlock = document.createElement("div");
    levelBlocks[level.id] = levelBlock;
    levelBlock.className = 'block';
    const levelName = document.createElement("p");
    levelName.textContent = level.name;
    levelBlock.appendChild(levelName);
    document.getElementById('background').appendChild(levelBlock);
    const markersDiv = document.createElement("div");
    markersDiv.className = "markers-div";
    if (level.category && categoriesOriginal[level.category]) {
        const colour = '#' + categoriesOriginal[level.category].colour.toString(16).padStart(6, '0');
        markersDiv.style.borderTopColor = colour;
    }
    levelBlock.appendChild(markersDiv);
    if (unsaved) {
        levelsOriginal[level.id].unsaved = true;
        levelBlock.classList.add('edited');
    }

    for (let [markerType, markerText] of [['solutions', 'S'], ['discord_channel', 'C'], ['discord_role', 'R'], ['unlocks', 'U'], ['extra_discord_role', 'E'], ['edited', '*']]) {
        const markerDiv = document.createElement('div');
        const markerSpan = document.createElement('span');
        markerSpan.classList.add('marker');
        markerSpan.classList.add(`marker_${markerType}`);
        markerSpan.textContent = markerText;
        markerDiv.appendChild(markerSpan);
        if (markerType !== 'edited') {
            markerDiv.className = 'tooltip';
            const markerTooltip = document.createElement('span');
            markerTooltip.className = 'tooltiptext';
            markerTooltip.textContent = markerType.replaceAll('_', ' ');
            markerDiv.appendChild(markerTooltip);
        }
        markersDiv.appendChild(markerDiv);
    }


    let checkForMakers = () => {
        for (let solutionType of ['solutions', 'unlocks'])
            levelBlock.classList.toggle(`has_${solutionType}`, levelsCurrent[level.id][solutionType].length > 0);
        for (let discordIdType of ['discord_channel', 'discord_role', 'extra_discord_role'])
            levelBlock.classList.toggle(`has_${discordIdType}`, !unsetValues.includes(levelsCurrent[level.id][discordIdType]));
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
        levelNameInput.value = levelsCurrent[level.id].name;
        levelNameInput.oninput = levelNameInput.onchange = () => {
            levelsCurrent[level.id].name = levelNameInput.value;
            levelName.textContent = levelsCurrent[level.id].name;
            checkLevelChange(level.id);
            checkForMakers();
        };

        for (let solutionType of ['solutions', 'unlocks']) {
            const solutionsInput = document.getElementById(`level_${solutionType}`);
            solutionsInput.value = levelsCurrent[level.id][solutionType].join('\n');
            solutionsInput.oninput = solutionsInput.onchange = () => {
                levelsCurrent[level.id][solutionType] = solutionsInput.value.split('\n').filter(e => e);
                checkLevelChange(level.id);
                checkForMakers()
            };
        }

        for (let discordIdType of ['discord_channel', 'discord_role', 'extra_discord_role']) {
            const discordIdInput = document.getElementById(`level_${discordIdType}`);
            discordIdInput.value = levelsCurrent[level.id][discordIdType];
            discordIdInput.oninput = discordIdInput.onchange = () => {
                levelsCurrent[level.id][discordIdType] = discordIdInput.value;
                checkLevelChange(level.id);
                checkForMakers()
            }
        }

        const levelCategoryList = document.getElementById('selectable_category_list');
        for (let otherLevelCategoryListItem of levelCategoryList.getElementsByTagName('li')) {
            otherLevelCategoryListItem.classList.remove('selected-category');
        }
        console.log(level.category);
        if (level.category)
            levelCategoryListItems[level.category].classList.add('selected-category');
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
        levelsCurrent[level.id].grid_location = [position.left + container.scrollLeft, position.top + container.scrollTop];
        checkLevelChange(level.id);
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
            createLevelBlock(level, false);
        }
    });
}

function createCategory(category, unsaved) {
    const categoryList = document.getElementById('editable_category_list');
    categoriesOriginal[category.id] = category;
    categoriesCurrent[category.id] = cloneObject(category);
    const categoryListItem = document.createElement('li');
    categoryListItem.textContent = category.name;
    categoryList.appendChild(categoryListItem);
    if (unsaved) {
        categoriesOriginal[category.id].unsaved = true;
    }
    categoryListItem.onclick = () => {
        document.getElementById('discord_category_name').value = category.name;
        document.getElementById('discord_category_id').value = category.discord_category;
        document.getElementById('discord_category_color').value = '#' + category.colour.toString(16).padStart(6, '0');
    };
    const levelCategoryList = document.getElementById('selectable_category_list');
    const levelCategoryListItem = categoryListItem.cloneNode(true);
    levelCategoryListItems[category.id] = levelCategoryListItem;
    levelCategoryListItem.onclick = () => {
        levelsCurrent[selectedLevelId].category = category.id;
        levelBlocks[selectedLevelId].getElementsByClassName('markers-div')[0].style.borderTopColor =
            '#' + category.colour.toString(16).padStart(6, '0');
        checkLevelChange(selectedLevelId);
        for (let otherLevelCategoryListItem of levelCategoryList.getElementsByTagName('li')) {
            otherLevelCategoryListItem.classList.remove('selected-category');
        }
        levelCategoryListItem.classList.add('selected-category');
    };
    levelCategoryList.appendChild(levelCategoryListItem);
}

function loadCategories(cb) {
    apiCall('/api/categories/').then(categories => {
        for (const[id, category] of Object.entries(categories)) {
            createCategory(category, false);
        }
        if (cb)
            cb();
    });
}

document.addEventListener('DOMContentLoaded', e => {
    if (localStorage.getItem('key') === null) {
        promptKey();
    }
    //loadConfig();
    loadCategories(loadLevels);
    document.getElementById('add_level_button').onclick = () => createLevelBlock({
        id: uuidv4(), name: '', parent_levels: [], child_levels: [], solutions: [], unlocks: [], discord_channel: null,
        discord_role: null, extra_discord_role: null, category: null, grid_location: [null, null]
    }, true);
    document.getElementById('save_levels_button').onclick = () => {
        for (let [levelId, levelChanged] of Object.entries(levelsChanged)) {
            const levelBlock = levelBlocks[levelId];
            if (levelChanged.id) {
                apiCall(`/api/levels/${levelId}`, 'PUT', levelChanged).then(r => {
                    if (r.message === 'ok') {
                        levelsOriginal[levelChanged.id] = cloneObject(levelChanged);
                        levelBlock.classList.toggle('edited', false);
                    } else {
                        levelBlock.classList.toggle('error', true);
                    }
                });
            } else {
                apiCall(`/api/levels/${levelId}`, 'DELETE').then(r => {
                    if (r.error)
                        alert(r.error);
                });
            }
        }
    }
    document.getElementById('delete_level_button').onclick = () => {
        const deletePopup = document.getElementById('delete_popup');
        const pageOverlay = document.getElementById('page-overlay')
        const deletePopupName = document.getElementById('delete_popup_name')
        deletePopup.style.display = 'block';
        pageOverlay.style.display = 'block';
        deletePopupName.textContent = levelsCurrent[selectedLevelId].name;
        document.getElementById('level_delete_ok_button').onclick = () => {
            levelsCurrent[selectedLevelId] = {};
            levelsChanged[selectedLevelId] = levelsCurrent[selectedLevelId];
            levelBlocks[selectedLevelId].remove();
            selectedLevelId = undefined;
            deletePopup.style.display = '';
            pageOverlay.style.display = '';
        }
        document.getElementById('level_delete_cancel_button').onclick = () => {
            deletePopup.style.display = '';
            pageOverlay.style.display = '';
        }
    };
    document.getElementById('category-menu-button').onclick = () => {
        document.getElementById('toolbar-level').style.display = '';
        document.getElementById('toolbar-configurations').style.display = '';
        document.getElementById('toolbar-category').style.display = 'block';
        for (let selectedLevel of document.querySelectorAll('.selected'))
            selectedLevel.classList.toggle('selected', false);
    };
    document.getElementById('configuration-menu-button').onclick = () => {
        document.getElementById('toolbar-level').style.display = '';
        document.getElementById('toolbar-category').style.display = '';
        document.getElementById('toolbar-configurations').style.display = 'block';
        document.getElementById('bot_token').type = 'password';
        document.getElementById('unlock_key').type = 'password';
        for (let selectedLevel of document.querySelectorAll('.selected'))
            selectedLevel.classList.toggle('selected', false);
    };
    document.getElementById('show_bot_token').onclick = () => {
        const targetElem = document.getElementById('bot_token');
        targetElem.type = (targetElem.type === 'password') ? 'text' : 'password';
    }
    document.getElementById('show_unlock_key').onclick = () => {
        const targetElem = document.getElementById('unlock_key');
        targetElem.type = (targetElem.type === 'password') ? 'text' : 'password';
    }
    const enableGrid = document.getElementById('enable_grid');
    enableGrid.onchange = e => {
        document.getElementById('main').style.fill = e.target.checked ? 'url(#bigGrid)' : '#1a1a21';
    };
    enableGrid.onchange({target: enableGrid});

    const enableTooltips = document.getElementById('enable_tooltips');
    const tooltipsStyle = document.createElement('style');
    document.body.appendChild(tooltipsStyle);
    enableTooltips.onchange = e => {
        if (e.target.checked) {
            if (tooltipsStyle.sheet.cssRules.length === 0) {
                tooltipsStyle.sheet.insertRule(".tooltip:hover .tooltiptext {visibility: visible;}", 0);
            }
        } else {
            if (tooltipsStyle.sheet.cssRules.length) {
                tooltipsStyle.sheet.deleteRule(0);
            }
        }
    };
    enableTooltips.onchange({target: enableTooltips});

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
                levelsCurrent[targetLevelId][targetKey] = r.id;
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
