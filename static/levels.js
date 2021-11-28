let levelsOriginal = {};
let levelsCurrent = {};
let levelsChanged = {};
let selectedLevelId;
let levelBlocks = {};
let lines = {};
let currentLine = null;
let lineMode = null;


function checkLevelChange(levelId) {
	const isChanged = compareObjects(levelsOriginal[levelId], levelsCurrent[levelId]);
	levelBlocks[levelId].classList.toggle('edited', isChanged);
	if (isChanged) {
		levelsChanged[levelId] = levelsCurrent[levelId];
		if (levelsChanged[levelId].id === undefined && levelsOriginal[levelId].unsaved)
			delete levelsChanged[levelId];
	} else {
		delete levelsChanged[levelId];
	}
	checkChanges(true);
}

function checkLevelMarkerChange(levelId) {
	const levelBlock = levelBlocks[levelId];
	const level = levelsCurrent[levelId];
	for (let solutionType of ['solutions', 'unlocks'])
		levelBlock.classList.toggle(`has_${solutionType}`, level[solutionType].length > 0);
	for (let discordIdType of ['discord_channel', 'discord_role', 'extra_discord_role'])
		levelBlock.classList.toggle(`has_${discordIdType}`, !unsetValues.includes(level[discordIdType]));
}

function createLine(startLevelId, endLevelId, addToLevels) {
	if (endLevelId + startLevelId in lines)
		deleteLine(endLevelId, startLevelId);
	if (!(startLevelId + endLevelId in lines)) {
		let startColour = '#424255';
		let endColour = '#424255';
		if (levelsCurrent[startLevelId].category)
			startColour = '#' + categoriesCurrent[levelsCurrent[startLevelId].category].colour.toString(16).padStart(6, '0');
		if (levelsCurrent[endLevelId].category)
			endColour = '#' + categoriesCurrent[levelsCurrent[endLevelId].category].colour.toString(16).padStart(6, '0');
		lines[startLevelId + endLevelId] = new LeaderLine(levelBlocks[startLevelId], levelBlocks[endLevelId], {
			startPlugColor: startColour,
			endPlugColor: endColour,
			gradient: true
		});
		if (addToLevels) {
			levelsCurrent[startLevelId].child_levels.push(endLevelId);
			checkLevelChange(startLevelId);
			levelsCurrent[endLevelId].parent_levels.push(startLevelId);
			checkLevelChange(endLevelId);
		}
	}
	for (let levelBlock of Object.values(levelBlocks))
		levelBlock.style.cursor = 'grab';
}

function deleteLine(startLevelId, endLevelId) {
	const line = lines[startLevelId + endLevelId];
	if (!line && (endLevelId + startLevelId) in lines)
		deleteLine(endLevelId, startLevelId);
	if (line) {
		levelsCurrent[startLevelId].child_levels = levelsCurrent[startLevelId].child_levels.filter(e => e !== endLevelId);
		checkLevelChange(startLevelId);
		levelsCurrent[endLevelId].parent_levels = levelsCurrent[endLevelId].parent_levels.filter(e => e !== startLevelId);
		checkLevelChange(endLevelId);
		line.remove();
		delete lines[startLevelId + endLevelId];
	}
	for (let levelBlock of Object.values(levelBlocks))
		levelBlock.style.cursor = 'grab';
}

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
	if (level.category && categoriesCurrent[level.category]) {
		const colour = '#' + categoriesCurrent[level.category].colour.toString(16).padStart(6, '0');
		markersDiv.style.borderTopColor = colour;
	}
	levelBlock.appendChild(markersDiv);
	if (unsaved) {
		levelsOriginal[level.id].unsaved = true;
		checkLevelChange(level.id);
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
	checkLevelMarkerChange(level.id);
	for (let parentLevelId of level.parent_levels) {
		if (parentLevelId in levelsCurrent && !(parentLevelId + level.id in lines))
			createLine(parentLevelId, level.id, false);
	}
	for (let childLevelId of level.child_levels) {
		if (childLevelId in levelsCurrent && !(level.id + childLevelId in lines))
			createLine(level.id, childLevelId, false);
	}
	levelBlock.onmousedown = e => {
		e.stopPropagation();
		if (currentLine) {
			if (currentLine.includes(level.id))
				return;
			currentLine.push(level.id);
			if (currentLine.length === 2) {
				if (lineMode === 'add')
					createLine(currentLine[0], currentLine[1], true);
				else if (lineMode === 'delete')
					deleteLine(currentLine[0], currentLine[1], true);
				currentLine = null;
				document.getElementById('add_line_button').classList.remove('active-button');
				document.getElementById('delete_line_button').classList.remove('active-button');
			}
			return;
		}
		selectedLevelId = level.id;
		for (let selectedLevel of document.querySelectorAll('.selected'))
			selectedLevel.classList.toggle('selected', false);
		levelBlock.classList.toggle('selected', true);
		document.getElementById('toolbar-level').style.display = 'block';
		document.getElementById('toolbar-category').style.display = '';
		document.getElementById('toolbar-settings').style.display = '';
		const levelNameInput = document.getElementById('level_name');
		levelNameInput.value = levelsCurrent[level.id].name;
		levelNameInput.oninput = levelNameInput.onchange = () => {
			levelsCurrent[level.id].name = levelNameInput.value;
			levelName.textContent = levelsCurrent[level.id].name;
			checkLevelChange(level.id);
			checkLevelMarkerChange(level.id);
		};
		for (let solutionType of ['solutions', 'unlocks']) {
			const solutionsInput = document.getElementById(`level_${solutionType}`);
			solutionsInput.value = levelsCurrent[level.id][solutionType].join('\n');
			solutionsInput.oninput = solutionsInput.onchange = () => {
				levelsCurrent[level.id][solutionType] = solutionsInput.value.split('\n').filter(e => e);
				checkLevelChange(level.id);
				checkLevelMarkerChange(level.id);
			};
		}
		for (let discordIdType of ['discord_channel', 'discord_role', 'extra_discord_role']) {
			const discordIdInput = document.getElementById(`level_${discordIdType}`);
			discordIdInput.value = levelsCurrent[level.id][discordIdType];
			discordIdInput.oninput = discordIdInput.onchange = () => {
				levelsCurrent[level.id][discordIdType] = discordIdInput.value;
				checkLevelChange(level.id);
				checkLevelMarkerChange(level.id);
			}
		}
		const levelCategoryList = document.getElementById('selectable_category_list');
		for (let otherLevelCategoryListItem of levelCategoryList.getElementsByTagName('li')) {
			otherLevelCategoryListItem.classList.remove('selected-category');
		}
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
		for (let line of Object.values(lines))
			line.position();
	};
	draggable.onDragEnd = function (position) {
		levelsCurrent[level.id].grid_location = [position.left + container.scrollLeft, position.top + container.scrollTop];
		checkLevelChange(level.id);
		for (let line of Object.values(lines))
			line.position();
	}
	draggable.autoScroll = {target: container};
}

function loadLevels(cb) {
	apiCall('/api/levels/').then(levels => {
		for (const [id, level] of Object.entries(levels)) {
			createLevelBlock(level, false);
		}
		if (cb)
			cb();
	});
}

function initLevels() {
	document.getElementById('add_level_button').onclick = () => createLevelBlock({
		id: uuidv4(), name: '', parent_levels: [], child_levels: [], solutions: [], unlocks: [], discord_channel: null,
		discord_role: null, extra_discord_role: null, category: null, grid_location: [null, null]
	}, true);
	document.getElementById('delete_level_button').onclick = () => {
		const deletePopup = document.getElementById('delete_popup');
		const pageOverlay = document.getElementById('page-overlay')
		const deletePopupName = document.getElementById('delete_popup_name')
		deletePopup.style.display = 'block';
		pageOverlay.style.display = 'block';
		deletePopupName.textContent = levelsCurrent[selectedLevelId].name;
		document.getElementById('level_delete_ok_button').onclick = () => {
			for (let parentLevelId of levelsCurrent[selectedLevelId].parent_levels)
				deleteLine(parentLevelId, selectedLevelId);
			for (let chileLevelId of levelsCurrent[selectedLevelId].child_levels)
				deleteLine(selectedLevelId, chileLevelId);
			levelsCurrent[selectedLevelId] = {
				delete_channel: document.getElementById('level_delete_channel').checked,
				delete_role: document.getElementById('level_delete_role').checked,
				delete_extra_role: document.getElementById('level_delete_extra_role').checked,
			};
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
	const addLineButton = document.getElementById('add_line_button');
	addLineButton.onclick = () => {
		currentLine = [];
		lineMode = 'add';
		addLineButton.classList.add('active-button');
		for (let levelBlock of Object.values(levelBlocks))
			levelBlock.style.cursor = 'crosshair';
	};
	const deleteLineButton = document.getElementById('delete_line_button');
	deleteLineButton.onclick = () => {
		currentLine = [];
		lineMode = 'delete';
		deleteLineButton.classList.add('active-button');
		for (let levelBlock of Object.values(levelBlocks))
			levelBlock.style.cursor = 'crosshair';
	};
	for (let [buttonId, inputId, targetKey] of [
		['level_create_channel', 'level_discord_channel', 'discord_channel'],
		['level_create_role', 'level_discord_role', 'discord_role'],
		['level_create_extra_role', 'level_extra_discord_role', 'discord_extra_role']
	]) {
		const buttonElem = document.getElementById(buttonId);
		const inputElem = document.getElementById(inputId);
		buttonElem.onclick = () => {
			const targetLevelId = selectedLevelId;
			const namePopup = document.getElementById('name_popup');
			const pageOverlay = document.getElementById('page-overlay');
			const okButton = document.getElementById('object_name_ok_button');
			const cancelButton = document.getElementById('object_name_cancel_button');
			namePopup.style.display = 'block';
			pageOverlay.style.display = 'block';
			document.getElementById('name_popup_name').textContent = levelsCurrent[selectedLevelId].name;
			document.getElementById('name_popup_object').textContent = targetKey.replaceAll('_', ' ');
			okButton.onclick = () => {
				const objectName = document.getElementById('object_name').value;
				if (!objectName)
					return;
				const data = {name: objectName};
				if (levelsCurrent[targetLevelId].category) {
					const category = categoriesCurrent[levelsCurrent[targetLevelId].category];
					if (category.discord_category)
						data['discord_category'] = category.discord_category;
				}
				const apiPath = (buttonId === 'level_create_channel') ? '/api/discord/channels/' : '/api/discord/roles/';
				apiCall(apiPath, 'POST', data).then(r => {
					if (r.error) {
						alert(r.error);
					} else {
						levelsCurrent[targetLevelId][targetKey] = r.id;
						if (selectedLevelId === targetLevelId)
							inputElem.value = r.id;
						namePopup.style.display = '';
						pageOverlay.style.display = '';
						checkLevelChange(targetLevelId);
						checkLevelMarkerChange(targetLevelId);
					}
				});
				okButton.onclick = undefined;
			};
			cancelButton.onclick = () => {
				namePopup.style.display = '';
				pageOverlay.style.display = '';
			};
		};
	}
	document.getElementById('container').addEventListener('scroll', AnimEvent.add(function () {
		for (let line of Object.values(lines))
			line.position();
	}));
	document.getElementById('background').onmousedown = e => {
		selectedLevelId = undefined;
		document.getElementById('toolbar-level').style.display = '';
		document.getElementById('toolbar-category').style.display = '';
		document.getElementById('toolbar-settings').style.display = '';
		for (let selectedLevel of document.querySelectorAll('.selected'))
			selectedLevel.classList.toggle('selected', false);
	};
}
