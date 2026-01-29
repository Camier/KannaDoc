import { describe, it, expect } from 'vitest';
import * as React from 'react';
import * as ReactDOM from 'react-dom';

describe('React Environment', () => {
  it('exports act', () => {
    console.log('React keys:', Object.keys(React));
    // @ts-ignore
    console.log('React.act:', React.act);
    
    // @ts-ignore
    expect(React.act).toBeDefined();
  });
});
