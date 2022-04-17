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

function checkChanges(updateSaveButton) {
	const haveSettingsChanged = Object.keys(settingsChanged).length > 0;
	const haveCategoriesChanged = Object.keys(categoriesChanged).length > 0;
	const haveLevelsChanged = Object.keys(levelsChanged).length > 0;
	const hasSomethingChanged = haveSettingsChanged || haveCategoriesChanged || haveLevelsChanged;
	document.getElementById('save_button').classList.toggle('changed', hasSomethingChanged);
	return hasSomethingChanged;
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
	const savingPopup = document.getElementById('saving_popup');
	const syncPopup = document.getElementById('sync_popup');
	const pageOverlay = document.getElementById('page-overlay')
	if (localStorage.getItem('key') === null) {
		promptKey();
	}
	loadSettings(loadCategories.bind(null, loadLevels));
	initLevels();
	initCategories();
	initSettings();
	document.getElementById('save_button').onclick = () => {
		let settingRequest, categoryRequest, levelRequest;
		savingPopup.style.display = 'block';
		pageOverlay.style.display = 'block';
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
					categoriesChanged = {};
					checkCategoryChange();
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
		settingRequest.then(() => categoryRequest).then(() => levelRequest).then(() => {
			checkChanges(true);
			savingPopup.style.display = '';
			pageOverlay.style.display = '';
		});
	}
	document.getElementById('sync_button').onclick = () => {
		const syncLog = document.getElementById('sync_log');
		const closeButton = document.getElementById('sync_close_button');
		syncPopup.style.display = 'block';
		pageOverlay.style.display = 'block';
		closeButton.setAttribute('disabled', true);
		apiCall('/api/sync/start', 'POST').then(r => {
			syncLog.value = '';
			let progress = 0;
			const queryStatus = () => {
				apiCall(`/api/sync/status?progress=${progress}`).then(r => {
					progress = r.progress;
					for (let line of r.log) {
						let ts = new Date(line[0] * 1000);
						let options = {'hour': '2-digit', 'minute': '2-digit', 'second': '2-digit'};
						let time = ts.toLocaleTimeString(options);
						syncLog.value += `${time} - ${line[1]}\n`
					}
					syncLog.scrollTop = syncLog.scrollHeight;
					if (!r.active) {
						closeButton.removeAttribute('disabled');
						closeButton.onclick = () => {
							syncPopup.style.display = '';
							pageOverlay.style.display = '';
						}
					} else {
						queryStatus();
					}
				});
			};
			queryStatus();
		});
	}
	window.onbeforeunload = function() {
		if (checkChanges(false)) {
			return "There are unsaved changes, pls stay? 🥺";
		}
	};
});
