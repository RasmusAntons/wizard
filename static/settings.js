function loadSettings() {
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
				apiCall('/api/config/', 'POST', {[key]: prompt('value')}).then(loadSettings);
			p.appendChild(editButton);
			const deleteButton = document.createElement('button');
			deleteButton.textContent = 'delete';
			deleteButton.onclick = () => apiCall(`/api/config/${key}`, 'DELETE').then(loadSettings);
			p.appendChild(deleteButton);
			optionsElem.appendChild(p);
		}
	});
}

function initSettings() {
	document.getElementById('settings-menu-button').onclick = () => {
		document.getElementById('toolbar-level').style.display = '';
		document.getElementById('toolbar-category').style.display = '';
		document.getElementById('toolbar-settings').style.display = 'block';
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
}
