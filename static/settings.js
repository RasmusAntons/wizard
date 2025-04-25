let settingsOriginal = {};
let settingsCurrent = {};
let settingsChanged = {};

const inputSettings = {
	'bot_token': 'text', 'key': 'text', 'guild': 'text', 'guild_invite': 'text', 'grid': 'check', 'tooltips': 'check', 'auth_in_link': 'check',
	'skipto_enable': 'check', 'embed_color': 'text', 'announcement_channel': 'text', 'announcement_template': 'text',
	'nickname_prefix': 'text', 'nickname_suffix': 'text', 'nickname_separator': 'text', 'nickname_enable': 'check', 'nickname_disable_all': 'check',
	'completionist_enable_nickname': 'check', 'completionist_badge': 'text',
	'completionist_enable_role': 'check', 'completionist_role': 'text',
	'admin_enable': 'check', 'admin_badge': 'text', 'admin_role': 'text', 'style': 'select',
	'public_url': 'text', 'enigmatics_token': 'text'
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

function nick(nickName, prefix, separator, suffix, levels) {
    const s = `${prefix}${levels.join(separator)}${suffix}`;
    return nickName.substring(0, 32 - s.length) + s.substring(0, 32);
}

function updateNicknamePreview() {
	const nicknamesDisabled = settingsCurrent['nickname_disable_all'] === 'true';
	if (nicknamesDisabled) {
		document.getElementById('discord_container').style.display = 'none';
		document.getElementById('nicknames_disabled_warning').style.display = 'block';
		return;
	} else {
		document.getElementById('discord_container').style.display = 'block';
		document.getElementById('nicknames_disabled_warning').style.display = 'none';
	}
	const discordContainer = document.getElementById('discord_container');
	const discordUsernames = discordContainer.querySelectorAll('.discord_username');
	const baseNames = {0: 'Catz', 1: 'weaver', 2: 'owlbotowlbotowlbotowlbotowlbotow'};
	const levels = {0: ['10'], 1: ['27', 'c', 'γ'], 2: ['50']};
	const prefix = settingsCurrent['nickname_prefix'];
	const suffix = settingsCurrent['nickname_suffix'];
	const separator = settingsCurrent['nickname_separator'];
	const enable = settingsCurrent['nickname_enable'];
	for (let [i, discordUsername] of discordUsernames.entries()) {
		if (enable === 'true')
			discordUsername.textContent = nick(baseNames[i], prefix, separator, suffix, levels[i]);
		else
			discordUsername.textContent = baseNames[i];
	}
}

function loadStyleOptions() {
	apiCall('/api/styles').then(styles => {
		const styleSelect = document.getElementById('setting_style');
		const currentStyle = settingsCurrent.style;
		for (let style of styles) {
			const option = document.createElement('option');
			option.value = style;
			option.textContent = style;
			if (style === currentStyle)
				option.selected = true;
			styleSelect.appendChild(option);
		}
	});
}

function loadSettings(cb) {
	apiCall('/api/settings').then(settings => {
		settingsOriginal = settings;
		settingsCurrent = cloneObject(settings);
		for (let [settingKey, settingType] of Object.entries(inputSettings)) {
			const settingInput = document.getElementById(`setting_${settingKey}`);
			if (!settingInput) {
				console.error(`missing settings widget for ${settingKey}`);
				continue;
			}
			if (settingType === 'text' || settingType === 'select') {
				if (settingKey in settings)
					settingInput.value = settings[settingKey];
				settingInput.oninput = settingInput.onchange = () => {
					settingsCurrent[settingKey] = settingInput.value;
					checkSettingChange(settingKey);
					if (settingKey.startsWith('nickname'))
						updateNicknamePreview();
				}
			} else if (settingType === 'check') {
				if (settingKey in settings) {
					settingInput.checked = JSON.parse(settings[settingKey]);
					settingInput.dispatchEvent(new Event('change'));
				}
				settingInput.addEventListener('change', () => {
					settingsCurrent[settingKey] = JSON.stringify(settingInput.checked);
					checkSettingChange(settingKey);
					if (settingKey.startsWith('nickname'))
						updateNicknamePreview();
				});
			}
		}
		loadStyleOptions();
		updateNicknamePreview();
		if (cb)
			cb();
	});
}

function initSettings() {
	document.getElementById('settings-menu-button').onclick = () => {
		document.getElementById('toolbar-level').style.display = '';
		document.getElementById('toolbar-category').style.display = '';
		document.getElementById('toolbar-nicknames').style.display = '';
		document.getElementById('toolbar-completionist').style.display = '';
		document.getElementById('toolbar-admin').style.display = '';
		document.getElementById('toolbar-settings').style.display = 'block';
		document.getElementById('setting_bot_token').type = 'password';
		document.getElementById('setting_key').type = 'password';
		for (let selectedLevel of document.querySelectorAll('.selected'))
			selectedLevel.classList.toggle('selected', false);
	};
	document.getElementById('nicknames-menu-button').onclick = () => {
		document.getElementById('toolbar-settings').style.display = '';
		document.getElementById('toolbar-nicknames').style.display = 'block';
	};
	document.getElementById('completionist-menu-button').onclick = () => {
		document.getElementById('toolbar-settings').style.display = '';
		document.getElementById('toolbar-completionist').style.display = 'block';
	};
	document.getElementById('admin-menu-button').onclick = () => {
		document.getElementById('toolbar-settings').style.display = '';
		document.getElementById('toolbar-admin').style.display = 'block';
	};
	const completionistCreateRole = document.getElementById('setting_completionist_create_role');
	completionistCreateRole.onclick = () => {
		const namePopup = document.getElementById('name_popup');
		const pageOverlay = document.getElementById('page-overlay');
		const okButton = document.getElementById('object_name_ok_button');
		const cancelButton = document.getElementById('object_name_cancel_button');
		namePopup.style.display = 'block';
		pageOverlay.style.display = 'block';
		document.getElementById('name_popup_name').textContent = 'completionist';
		document.getElementById('name_popup_object').textContent = 'discord role';
		okButton.onclick = () => {
			const objectName = document.getElementById('object_name').value;
			if (!objectName)
				return;
			apiCall('/api/discord/roles/', 'POST', {'name': objectName}).then(r => {
				if (r.error) {
					alert(r.error);
				} else {
					document.getElementById('setting_completionist_role').value = r.id;
					settingsCurrent['completionist_role'] = r.id;
					checkSettingChange('completionist_role');
					namePopup.style.display = '';
					pageOverlay.style.display = '';
				}
			});
			okButton.onclick = undefined;
		};
		cancelButton.onclick = () => {
			namePopup.style.display = '';
			pageOverlay.style.display = '';
		};
	};
	for (let key of ['bot_token', 'key', 'enigmatics_token']) {
		document.getElementById(`show_${key}`).onclick = () => {
			const targetElem = document.getElementById(`setting_${key}`);
			targetElem.type = (targetElem.type === 'password') ? 'text' : 'password';
		};
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
