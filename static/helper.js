let snapDistance = 20;
const unsetValues = [null, undefined, ""];
let unsavedChanges = false;

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
	unsavedChanges = haveSettingsChanged || haveCategoriesChanged || haveLevelsChanged;
	for (let button_id of ['save_button', 'sync_button'])
		document.getElementById(button_id).classList.toggle('changed', unsavedChanges);
	document.getElementById('sync_button_label').textContent = unsavedChanges ? 'save & sync' : 'sync';
	return unsavedChanges;
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

function save() {
	const savingPopup = document.getElementById('saving_popup');
	const pageOverlay = document.getElementById('page-overlay')
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
	return settingRequest.then(() => categoryRequest).then(() => levelRequest).then(() => {
		checkChanges(true);
		savingPopup.style.display = '';
		pageOverlay.style.display = '';
	});
}

function sync() {
	const syncPopup = document.getElementById('sync_popup');
	const pageOverlay = document.getElementById('page-overlay')
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

function exportData() {
	apiCall('/api/userdata').then(userdata => {
		const result = {
			settings: settingsOriginal,
			categories: categoriesOriginal,
			levels: levelsOriginal,
			userdata: userdata
		};
		const blob = new Blob([JSON.stringify(result)], {type: 'application/json'});
		const a = document.createElement('a');
		a.href = URL.createObjectURL(blob);
		a.setAttribute('download', 'wizard_data.json');
		document.body.appendChild(a);
		a.click();
		document.removeChild(a);
	});
}

function importData() {
	const fileInput = document.getElementById('import_file_input');
	if (fileInput.files.length === 0) {
		alert('no file selected!');
		return;
	}
	const reader = new FileReader();
	reader.onload = (event) => {
		let data = null;
		try {
			data = JSON.parse(event.target.result);
		} catch (e) {
			console.error(e);
			alert('error parsing json');
			return;
		}
		document.getElementById('saving_popup').style.display = 'block';
		document.getElementById('page-overlay').style.display = 'block';
		let settingRequest, categoryRequest, levelRequest, userdataRequest;
		if (Object.keys(data.settings).length) {
			settingRequest = apiCall(`/api/settings`, 'PATCH', data.settings);
		} else {
			settingRequest = new Promise(r => r());
		}
		if (Object.keys(data.categories).length > 0) {
			categoryRequest = apiCall('/api/categories/', 'PATCH', data.levels);
		} else {
			categoryRequest = new Promise(r => r());
		}
		if (Object.keys(data.levels).length > 0) {
			levelRequest = apiCall('/api/levels/', 'PATCH', data.levels);
		} else {
			levelRequest = new Promise(r => r());
		}
		if (Object.keys(data.userdata).length > 0) {
			userdataRequest = apiCall('/api/userdata', 'PATCH', data.userdata);
		} else {
			userdataRequest = new Promise(r => r());
		}
		return settingRequest.then(() => categoryRequest).then(() => levelRequest).then(() => userdataRequest)
			.then(() => {location.reload()});
	};
	reader.readAsText(fileInput.files[0]);
}

document.addEventListener('DOMContentLoaded', e => {
	if (localStorage.getItem('key') === null) {
		promptKey();
	}
	loadSettings(loadCategories.bind(null, loadLevels));
	initLevels();
	initCategories();
	initSettings();
	document.getElementById('save_button').onclick = save;
	document.getElementById('sync_button').onclick = () => {
		if (unsavedChanges)
			save().then(sync);
		else
			sync();
	}
	document.getElementById('export_button').onclick = exportData;
	document.getElementById('import_button').onclick = () => {
		document.getElementById('import_popup').style.display = 'block';
		document.getElementById('page-overlay').style.display = 'block';
	};
	document.getElementById('import_ok_button').onclick = () => {
		importData();
	};
	document.getElementById('import_cancel_button').onclick = () => {
		document.getElementById('import_popup').style.display = 'none';
		document.getElementById('page-overlay').style.display = 'none';
	};
	window.onbeforeunload = function() {
		if (checkChanges(false)) {
			return "There are unsaved changes, pls stay? 🥺";
		}
	};
});
