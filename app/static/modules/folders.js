import {$} from './dom.js';

const arrowSvg = axis => {
  const paths = {
    up: '<path d="M12 5.5v13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M5.5 12 12 5.5 18.5 12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
    down: '<path d="M12 5.5v13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M5.5 12 12 18.5 18.5 12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
    left: '<path d="M5.5 12h13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M12 5.5 5.5 12 12 18.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
    right: '<path d="M5.5 12h13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M12 5.5 18.5 12 12 18.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>'
  };
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[axis] || paths.right}</svg>`;
};

export function initFolders({confirmDelete, errText}) {
  const folderButtons = [...document.querySelectorAll('.fold[data-folder]')];
  const folderTitle = $('#folder-title');
  const folderForm = $('#folder-form');
  const folderNameField = $('#folder-form [name=name]');
  const folderMsg = $('#fe-msg');
  const deleteFolderButton = $('#delete-folder');
  const folderSheet = $('#folder-sheet');
  const folderSheetClose = $('#folder-sheet .close');
  const folderEditButton = $('#folder-edit');
  const folderBackButton = $('#folder-back');
  const folderRow = $('.folders') || document.createElement('div');

  let curFolder = null;

  const folderEls = () => [...folderRow.querySelectorAll('.fold[data-folder]')];
  const getFolderNode = folderId => folderRow.querySelector(`.fold[data-folder="${folderId}"]`);

  const openFolderSheet = folder => {
    curFolder = folder;
    folderTitle.textContent = folder ? 'Edit folder' : 'New folder';
    folderNameField.value = folder ? folder.name : '';
    folderMsg.textContent = '';
    deleteFolderButton.hidden = !folder;
    folderSheet.hidden = false;
    folderNameField.focus();
  };

  const closeFolderSheet = () => {
    folderSheet.hidden = true;
  };

  const updateFolderNode = (folderId, payload) => {
    const folder = getFolderNode(folderId);
    if (!folder) return;
    folder.dataset.name = payload.name;
    const label = folder.querySelector('.title, .folder-name, [data-role="folder-name"]');
    if (label) label.textContent = payload.name;
  };

  folderButtons.forEach(folder => {
    folder.onclick = () => {
      location.href = folder.classList.contains('on') ? '/' : '/?folder=' + folder.dataset.folder;
    };
  });

  if (folderEditButton) {
    folderBackButton.onclick = () => {
      location.href = '/';
    };
    folderEditButton.onclick = () => openFolderSheet({...folderEditButton.dataset});
  }

  folderSheetClose.onclick = closeFolderSheet;

  folderForm.onsubmit = async event => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(folderForm));
    const response = await fetch(curFolder ? '/api/folders/' + curFolder.id : '/api/folders', {
      method: curFolder ? 'PUT' : 'POST',
      body: new URLSearchParams(new FormData(folderForm)),
    });

    if (!response.ok) {
      folderMsg.textContent = await errText(response);
      return;
    }

    // Edit can be patched locally; create still needs a page refresh for new layout.
    if (curFolder) {
      updateFolderNode(curFolder.id, payload);
      closeFolderSheet();
      return;
    }

    location.reload();
  };

  deleteFolderButton.onclick = () => confirmDelete('folder', curFolder);

  const HOLD_MS = 2000;
  let folderTimer = null;
  let folderStart = null;
  let movingFolder = null;
  let swallowFolder = false;

  const isVertical = () => getComputedStyle(folderRow).gridTemplateColumns.split(' ').length === 1;

  const saveFolderOrder = async () => {
    const body = new URLSearchParams();
    folderEls().forEach(folder => body.append('ids', folder.dataset.folder));
    const response = await fetch('/api/folders/order', {method: 'POST', body});
    if (!response.ok) {
      alert('Could not save folder order.');
      location.reload();
    }
  };

  const syncFolderArrows = () => {
    if (!movingFolder) return;
    const vertical = isVertical();
    const all = folderEls();
    const index = all.indexOf(movingFolder);
    const [prev, next] = movingFolder.querySelectorAll('.folder-arrow');
    prev.innerHTML = arrowSvg(vertical ? 'up' : 'left');
    next.innerHTML = arrowSvg(vertical ? 'down' : 'right');
    prev.setAttribute('aria-label', vertical ? 'Move up' : 'Move left');
    next.setAttribute('aria-label', vertical ? 'Move down' : 'Move right');
    prev.disabled = index === 0;
    next.disabled = index === all.length - 1;
  };

  const shiftFolder = async dir => {
    const all = folderEls();
    const other = all[all.indexOf(movingFolder) + dir];
    if (!other) return;
    dir < 0 ? other.before(movingFolder) : other.after(movingFolder);
    movingFolder.scrollIntoView({block: 'nearest'});
    syncFolderArrows();
    await saveFolderOrder();
  };

  const enterFolderMove = folder => {
    movingFolder = folder;
    swallowFolder = true;
    folder.classList.remove('holding');
    folder.classList.add('moving-folder');
    for (const cls of ['prev', 'next']) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'folder-arrow ' + cls;
      button.onclick = event => {
        event.stopPropagation();
        shiftFolder(cls === 'prev' ? -1 : 1);
      };
      folder.append(button);
    }
    syncFolderArrows();
  };

  const exitFolderMove = () => {
    if (!movingFolder) return;
    movingFolder.querySelectorAll('.folder-arrow').forEach(arrow => arrow.remove());
    movingFolder.classList.remove('moving-folder');
    movingFolder = null;
  };

  const cancelFolderHold = folder => {
    clearTimeout(folderTimer);
    folder.classList.remove('holding');
    folderStart = null;
  };

  for (const folder of folderEls()) {
    folder.addEventListener('contextmenu', event => event.preventDefault());
    folder.addEventListener('keydown', event => {
      if (event.target === folder && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        folder.click();
      }
    });
    folder.addEventListener('pointerdown', event => {
      if (movingFolder || event.button > 0 || event.target.closest('button,input,select,summary')) return;
      folderStart = [event.clientX, event.clientY];
      folder.classList.add('holding');
      folderTimer = setTimeout(() => enterFolderMove(folder), HOLD_MS);
    });
    folder.addEventListener('pointermove', event => {
      if (folderStart && Math.hypot(event.clientX - folderStart[0], event.clientY - folderStart[1]) > 10) cancelFolderHold(folder);
    });
    for (const name of ['pointerup', 'pointercancel', 'pointerleave']) {
      folder.addEventListener(name, () => {
        cancelFolderHold(folder);
        if (movingFolder) setTimeout(() => { swallowFolder = false; }, 400);
      });
    }
  }

  document.addEventListener('click', event => {
    if (swallowFolder) {
      swallowFolder = false;
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (movingFolder && event.target.closest('.folder-arrow')) return;
    if (movingFolder && event.target.closest('.fold')) {
      event.preventDefault();
      event.stopPropagation();
      exitFolderMove();
      return;
    }
    if (movingFolder) exitFolderMove();
  }, true);

  addEventListener('keydown', event => {
    if (event.key === 'Escape') exitFolderMove();
  });
}
