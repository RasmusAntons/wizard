let levelsOriginal = {};
let levelsCurrent = {};
let levelsChanged = {};
let selectedLevelId;
let levelBlocks = {};
let lines = {};
let currentLine = null;


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
}

function createLine(startLevelId, endLevelId) {
	let startColour = '#424255';
	let endColour =  '#424255';
	if (levelsCurrent[startLevelId].category)
		startColour = '#' + categoriesCurrent[levelsCurrent[startLevelId].category].colour.toString(16).padStart(6, '0');
	if (levelsCurrent[endLevelId].category)
		endColour = '#' + categoriesCurrent[levelsCurrent[endLevelId].category].colour.toString(16).padStart(6, '0');
	lines[startLevelId + endLevelId] = new LeaderLine(levelBlocks[startLevelId], levelBlocks[endLevelId], {
		startPlugColor: startColour,
		endPlugColor: endColour,
		gradient: true
	});
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
	let checkForMakers = () => {
		for (let solutionType of ['solutions', 'unlocks'])
			levelBlock.classList.toggle(`has_${solutionType}`, levelsCurrent[level.id][solutionType].length > 0);
		for (let discordIdType of ['discord_channel', 'discord_role', 'extra_discord_role'])
			levelBlock.classList.toggle(`has_${discordIdType}`, !unsetValues.includes(levelsCurrent[level.id][discordIdType]));
	}
	checkForMakers();
	levelBlock.onmousedown = e => {
		e.stopPropagation();
		if (currentLine) {
			if (currentLine.includes(level.id))
				return;
			currentLine.push(level.id);
			if (currentLine.length === 2) {
				createLine(currentLine[0], currentLine[1]);
				currentLine = null;
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
	document.getElementById('add_line_button').onclick = () => {
		currentLine = [];
		for (let levelBlock of Object.values(levelBlocks))
			levelBlock.style.cursor = 'crosshair';
	};
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
