let settingsOriginal = {};
let settingsCurrent = {};
let settingsChanged = {};

const inputSettings = {
	'bot_token': 'text', 'key': 'text', 'guild': 'text', 'grid': 'check', 'tooltips': 'check',
	'nickname_prefix': 'text', 'nickname_suffix': 'text', 'nickname_separator': 'text'
};

function checkSettingChange(settingKey) {
	if (settingKey) {
		if (settingsOriginal[settingKey] !== settingsCurrent[settingKey])
			settingsChanged[settingKey] = settingsCurrent[settingKey];
		else
			delete settingsChanged[settingKey];
	}
	document.getElementById('settings-menu-button').classList.toggle('changed',
		Object.keys(settingsChanged).length);
	checkChanges(true);
}

function loadSettings(cb) {
	apiCall('/api/settings').then(settings => {
		settingsOriginal = settings;
		settingsCurrent = cloneObject(settings);
		for (let [settingKey, settingType] of Object.entries(inputSettings)) {
			const settingInput = document.getElementById(`setting_${settingKey}`);
			if (settingType === 'text') {
				if (settingKey in settings)
					settingInput.value = settings[settingKey];
				settingInput.oninput = settingInput.onchange = () => {
					settingsCurrent[settingKey] = settingInput.value;
					checkSettingChange(settingKey);
				}
			} else if (settingType === 'check') {
				if (settingKey in settings) {
					settingInput.checked = JSON.parse(settings[settingKey]);
					settingInput.dispatchEvent(new Event('change'));
				}
				settingInput.addEventListener('change', () => {
					settingsCurrent[settingKey] = JSON.stringify(settingInput.checked);
					checkSettingChange(settingKey);
				});
			}
		}
		if (cb)
			cb();
	});
}

function initSettings() {
	document.getElementById('settings-menu-button').onclick = () => {
		document.getElementById('toolbar-level').style.display = '';
		document.getElementById('toolbar-category').style.display = '';
		document.getElementById('toolbar-nicknames').style.display = '';
		document.getElementById('toolbar-settings').style.display = 'block';
		document.getElementById('setting_bot_token').type = 'password';
		document.getElementById('setting_key').type = 'password';
		for (let selectedLevel of document.querySelectorAll('.selected'))
			selectedLevel.classList.toggle('selected', false);
	};
	document.getElementById('nicknames-menu-button').onclick = () => {
		document.getElementById('toolbar-settings').style.display = '';
		document.getElementById('toolbar-nicknames').style.display = 'block';
	}
	document.getElementById('show_bot_token').onclick = () => {
		const targetElem = document.getElementById('setting_bot_token');
		targetElem.type = (targetElem.type === 'password') ? 'text' : 'password';
	}
	document.getElementById('show_unlock_key').onclick = () => {
		const targetElem = document.getElementById('setting_key');
		targetElem.type = (targetElem.type === 'password') ? 'text' : 'password';
	}
	const enableGrid = document.getElementById('setting_grid');
	enableGrid.onchange = e => {
		document.getElementById('main').style.fill = e.target.checked ? 'url(#bigGrid)' : '#1a1a21';
	};
	enableGrid.onchange({target: enableGrid});
	const enableTooltips = document.getElementById('setting_tooltips');
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
}
