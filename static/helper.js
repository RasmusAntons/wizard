let snapDistance = 20;
const unsetValues = [null, undefined, ""];

function promptKey() {
	const newKey = prompt('key');
	if (newKey)
		localStorage.setItem('key', newKey);
}

/**
 * Generate random UUIDv4
 * https://stackoverflow.com/a/2117523
 */
function uuidv4() {
	return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
		(c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
	);
}

function apiCall(path, method, data) {
	const key = localStorage.getItem('key');
	const url = new URL(path, document.location.origin);
	const options = {headers: {'Authorization': `Bearer ${key}`}};
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

function compareObjects(objA, objB) {
	for (let key of Object.getOwnPropertyNames(objA)) {
		if (JSON.stringify(objA[key]) !== JSON.stringify(objB[key])) {
			if (unsetValues.includes(objA[key]) && unsetValues.includes(objB[key])) {
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

document.addEventListener('DOMContentLoaded', e => {
	if (localStorage.getItem('key') === null) {
		promptKey();
	}
	loadSettings(loadCategories.bind(null, loadLevels));
	initLevels();
	initCategories();
	initSettings();
	document.getElementById('save_button').onclick = () => {
		let settingRequest, categoryRequest, levelRequest;
		if (Object.keys(settingsChanged).length) {
			settingRequest = apiCall(`/api/settings`, 'PATCH', settingsChanged).then(r => {
				settingsOriginal = cloneObject(settingsCurrent);
				if ('key' in settingsChanged)
					localStorage.setItem('key', settingsChanged['key']);
				settingsChanged = {};
				checkSettingChange();
			});
		} else {
			settingRequest = new Promise(r => r());
		}
		if (Object.keys(categoriesChanged).length > 0) {
			categoryRequest = apiCall('/api/categories/', 'PATCH', categoriesChanged).then(r => {
				if (r.error) {
					alert(r.error);
				} else {
					for (let [categoryId, category] of Object.entries(categoriesChanged)) {
						if (category.id) {
							categoriesOriginal[categoryId] = cloneObject(category);
						} else {
							delete categoriesOriginal[categoryId];
							delete categoriesCurrent[categoryId];
						}
					}
					checkCategoryChange();
					categoriesChanged = {};
				}
			});
		} else {
			categoryRequest = new Promise(r => r());
		}
		if (Object.keys(levelsChanged).length > 0) {
			levelRequest = apiCall('/api/levels/', 'PATCH', levelsChanged).then(r => {
				if (r.error) {
					alert(r.error);
				} else {
					for (let [levelId, level] of Object.entries(levelsChanged)) {
						if (level.id) {
							levelsOriginal[levelId] = cloneObject(level);
							levelBlocks[levelId].classList.toggle('edited', false);
						} else {
							delete levelsOriginal[levelId];
							delete levelsCurrent[levelId];
						}
					}
					levelsChanged = {};
				}
			});
		} else {
			levelRequest = new Promise(r => r());
		}
		settingRequest.then(categoryRequest).then(levelRequest).then(() => console.log('save complete'));
	}

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
});
