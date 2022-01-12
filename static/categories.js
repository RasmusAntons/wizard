let categoriesOriginal = {};
let categoriesCurrent = {};
let categoriesChanged = {};
let selectedCategoryId;
let categoryListItems = {};
let levelCategoryListItems = {};

function checkCategoryChange(categoryId) {
	if (categoryId) {
		const isChanged = compareObjects(categoriesOriginal[categoryId], categoriesCurrent[categoryId]);
		if (isChanged) {
			categoriesChanged[categoryId] = categoriesCurrent[categoryId];
			if (categoriesChanged[categoryId].id === undefined && categoriesOriginal[categoryId].unsaved)
				delete categoriesChanged[categoryId];
		} else {
			delete categoriesChanged[categoryId];
		}
	}
	document.getElementById('category-menu-button').classList.toggle('changed',
		Object.keys(categoriesChanged).length);
	checkChanges(true);
}

function createCategory(category, unsaved) {
	const categoryList = document.getElementById('editable_category_list');
	categoriesOriginal[category.id] = category;
	categoriesCurrent[category.id] = cloneObject(category);
	const categoryListItem = document.createElement('li');
	categoryListItems[category.id] = categoryListItem;
	categoryListItem.textContent = category.name;
	categoryListItem.style.borderLeftColor = '#' + category.colour.toString(16).padStart(6, '0');
	categoryList.appendChild(categoryListItem);
	if (unsaved) {
		categoriesOriginal[category.id].unsaved = true;
		checkCategoryChange(category.id);
	}
	categoryListItem.onclick = () => {
		if (selectedCategoryId)
			categoryListItems[selectedCategoryId].classList.remove('selected-category');
		selectedCategoryId = category.id;
		categoryListItem.classList.add('selected-category');
		const categoryNameInput = document.getElementById('discord_category_name');
		categoryNameInput.value = category.name;
		categoryNameInput.disabled = false;
		categoryNameInput.oninput = categoryNameInput.onchange = () => {
			categoryListItems[category.id].textContent = categoryNameInput.value;
			levelCategoryListItems[category.id].textContent = categoryNameInput.value;
			categoriesCurrent[category.id].name = categoryNameInput.value;
			checkCategoryChange(category.id);
		};
		const categoryIdInput = document.getElementById('discord_category_id');
		categoryIdInput.value = categoriesCurrent[category.id].discord_category;
		categoryIdInput.disabled = false;
		categoryIdInput.oninput = categoryIdInput.onchange = () => {
			categoriesCurrent[category.id].discord_category = categoryIdInput.value;
			checkCategoryChange(category.id);
		};
		const categoryCreateButton = document.getElementById('discord_category_create');
		categoryCreateButton.disabled = false;
		categoryCreateButton.onclick = () => {
			const namePopup = document.getElementById('name_popup');
			const pageOverlay = document.getElementById('page-overlay');
			const okButton = document.getElementById('object_name_ok_button');
			const cancelButton = document.getElementById('object_name_cancel_button');
			namePopup.style.display = 'block';
			pageOverlay.style.display = 'block';
			document.getElementById('name_popup_name').textContent = categoriesCurrent[category.id].name;
			document.getElementById('name_popup_object').textContent = 'discord category';
			okButton.onclick = () => {
				const objectName = document.getElementById('object_name').value;
				if (!objectName)
					return;
				apiCall('/api/discord/categories/', 'POST', {'name': objectName}).then(r => {
					if (r.error) {
						alert(r.error);
					} else {
						categoriesCurrent[category.id].discord_category = r.id;
						if (selectedCategoryId === category.id)
							categoryIdInput.value = r.id;
						namePopup.style.display = '';
						pageOverlay.style.display = '';
						checkCategoryChange(category.id);
					}
				});
				okButton.onclick = undefined;
			};
			cancelButton.onclick = () => {
				namePopup.style.display = '';
				pageOverlay.style.display = '';
			};
		};
		const categoryColourInput = document.getElementById('discord_category_color');
		categoryColourInput.value = '#' + categoriesCurrent[category.id].colour.toString(16).padStart(6, '0');
		categoryColourInput.disabled = false;
		categoryColourInput.onchange = () => {
			const newColour = parseInt(categoryColourInput.value.substr(1), 16);
			categoriesCurrent[category.id].colour = newColour;
			categoryListItems[category.id].style.borderLeftColor = categoryColourInput.value;
			levelCategoryListItems[category.id].style.borderLeftColor = categoryColourInput.value;
			for (let level of Object.values(levelsCurrent)) {
				if (level.category === category.id) {
					levelBlocks[level.id].getElementsByClassName('markers-div')[0].style.borderTopColor = categoryColourInput.value;
					for (let parentLevelId of level.parent_levels) {
						if (parentLevelId + level.id in lines)
							lines[parentLevelId + level.id].endPlugColor = categoryColourInput.value;
					}
					for (let childLevelId of level.child_levels) {
						if (level.id + childLevelId in lines)
							lines[level.id + childLevelId].startPlugColor = categoryColourInput.value;
					}
				}
			}
			checkCategoryChange(category.id);
		};
		const categoryRemoveButton = document.getElementById('remove_category_button');
		categoryRemoveButton.disabled = false;
		categoryRemoveButton.onclick = () => {
			categoryListItems[category.id].remove();
			levelCategoryListItems[category.id].remove();
			categoriesCurrent[category.id] = {};
			checkCategoryChange(category.id);
			for (let level of Object.values(levelsCurrent)) {
				if (level.category === category.id) {
					level.category = null;
					levelBlocks[level.id].getElementsByClassName('markers-div')[0].style.borderTopColor = '';
					checkLevelChange(level.id);
				}
			}
		};
	};
	const levelCategoryList = document.getElementById('selectable_category_list');
	const levelCategoryListItem = categoryListItem.cloneNode(true);
	levelCategoryListItems[category.id] = levelCategoryListItem;
	levelCategoryListItem.onclick = () => {
		levelsCurrent[selectedLevelId].category = category.id;
		const cssColour = '#' + categoriesCurrent[category.id].colour.toString(16).padStart(6, '0');
		levelBlocks[selectedLevelId].getElementsByClassName('markers-div')[0].style.borderTopColor = cssColour;
		for (let parentLevelId of levelsCurrent[selectedLevelId].parent_levels) {
			if (parentLevelId + selectedLevelId in lines)
				lines[parentLevelId + selectedLevelId].endPlugColor = cssColour;
		}
		for (let childLevelId of levelsCurrent[selectedLevelId].child_levels) {
			if (selectedLevelId + childLevelId in lines)
				lines[selectedLevelId + childLevelId].startPlugColor = cssColour;
		}
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
		for (const [id, category] of Object.entries(categories)) {
			createCategory(category, false);
		}
		if (cb)
			cb();
	});
}

function initCategories() {
	document.getElementById('category-menu-button').onclick = () => {
		document.getElementById('toolbar-level').style.display = '';
		document.getElementById('toolbar-settings').style.display = '';
		document.getElementById('toolbar-nicknames').style.display = '';
		document.getElementById('toolbar-category').style.display = 'block';
		if (selectedCategoryId)
			categoryListItems[selectedCategoryId].classList.remove('selected-category');
		const categoryNameInput = document.getElementById('discord_category_name');
		categoryNameInput.disabled = true;
		categoryNameInput.value = null;
		const categoryIdInput = document.getElementById('discord_category_id');
		categoryIdInput.disabled = true;
		categoryIdInput.value = null;
		const categoryColourInput = document.getElementById('discord_category_color');
		categoryColourInput.value = null;
		categoryColourInput.disabled = true;
		const categoryRemoveButton = document.getElementById('remove_category_button');
		categoryRemoveButton.disabled = true;
		document.getElementById('discord_category_create').disabled = true;
		for (let selectedLevel of document.querySelectorAll('.selected'))
			selectedLevel.classList.toggle('selected', false);
	};
	document.getElementById('add_category_button').onclick = () => {
		const categoryId = uuidv4();
		createCategory({id: categoryId, name: '', discord_category: null, colour: 0x232330}, true);
		categoryListItems[categoryId].click();

	}
}
