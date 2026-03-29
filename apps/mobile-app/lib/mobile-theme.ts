export type MobilePalette = ReturnType<typeof getMobilePalette>;

export function getMobilePalette(colorScheme: string | null | undefined) {
  if (colorScheme === 'dark') {
    return {
      background: '#0d1216',
      panel: '#141b20',
      subtlePanel: '#10171b',
      hero: '#193038',
      heroSoft: '#39535d',
      heroBorder: '#3c6875',
      heroText: '#f3f7f8',
      heroSubtle: '#b5c8ce',
      eyebrow: '#8bd4eb',
      text: '#f5f7f7',
      muted: '#b8c3c7',
      placeholder: '#7e8a91',
      border: '#223038',
      input: '#0f1519',
      primary: '#8bd4eb',
      primaryText: '#0d1216',
      danger: '#ff8b8b',
      goodMuted: '#123126',
      goodText: '#88ddb0',
      warnMuted: '#372717',
      warnText: '#ffcb8b',
      metricA: '#8bd4eb',
      metricB: '#88ddb0',
      metricC: '#ffcb8b',
    };
  }

  return {
    background: '#f2ede6',
    panel: '#fffaf3',
    subtlePanel: '#f7f1e9',
    hero: '#183a43',
    heroSoft: '#4b686f',
    heroBorder: '#5f8790',
    heroText: '#f8f6f1',
    heroSubtle: '#c7d9dd',
    eyebrow: '#9adff1',
    text: '#172026',
    muted: '#5c6770',
    placeholder: '#87929b',
    border: '#ded4c7',
    input: '#fffdf9',
    primary: '#183a43',
    primaryText: '#f8f6f1',
    danger: '#b33f36',
    goodMuted: '#dff4e6',
    goodText: '#24553a',
    warnMuted: '#f9ecd7',
    warnText: '#7a4a11',
    metricA: '#6fbfd8',
    metricB: '#93c89a',
    metricC: '#ddb36f',
  };
}
