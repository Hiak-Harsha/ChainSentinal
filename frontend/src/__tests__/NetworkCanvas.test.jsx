import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import NetworkCanvas from '../components/NetworkCanvas';

let mockCyInstance;

vi.mock('cytoscape', () => {
  return {
    default: vi.fn(() => {
      mockCyInstance = {
        on: vi.fn(),
        destroy: vi.fn(),
        fit: vi.fn(),
        zoom: vi.fn(() => 1),
        elements: vi.fn(() => ({ remove: vi.fn() })),
        add: vi.fn(),
        layout: vi.fn(() => ({ run: vi.fn() })),
        nodes: vi.fn(() => ({ select: vi.fn() })),
      };
      return mockCyInstance;
    }),
  };
});

vi.mock('../api', () => ({
  api: {
    getEntities: vi.fn(() => Promise.resolve([
      { entity_id: 'ENT_TEST_1', entity_type: 'EXCHANGE', member_count: 5 },
      { entity_id: 'ENT_TEST_2', entity_type: 'MIXER', member_count: 12 },
    ])),
    getEgoSubgraph: vi.fn(() => Promise.resolve({
      nodes: [
        { id: 'ENT_TEST_1', label: 'ENT_TEST_1', type: 'Entity' },
        { id: 'addr_1', label: '1A1zP1...', type: 'Address' },
      ],
      edges: [
        { id: 'e1', source: 'addr_1', target: 'ENT_TEST_1', label: 'member_of', weight: 1.0 },
      ],
    })),
  },
}));

describe('NetworkCanvas Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders canvas container, search input, layout controls and cluster button', () => {
    render(<NetworkCanvas centerId="ENT_TEST_1" />);

    expect(screen.getByPlaceholderText(/Search or enter Entity ID/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Expand/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cluster/i })).toBeInTheDocument();
  });

  it('honors the hidden prop by applying display: none to container', () => {
    const { container: visibleContainer } = render(<NetworkCanvas centerId="ENT_TEST_1" hidden={false} />);
    const visibleRoot = visibleContainer.firstChild;
    expect(visibleRoot).toHaveStyle({ display: 'flex' });

    const { container: hiddenContainer } = render(<NetworkCanvas centerId="ENT_TEST_1" hidden={true} />);
    const hiddenRoot = hiddenContainer.firstChild;
    expect(hiddenRoot).toHaveStyle({ display: 'none' });
  });

  it('triggers onCenterIdChange when Expand button is clicked', () => {
    const onCenterIdChange = vi.fn();
    render(<NetworkCanvas centerId="" onCenterIdChange={onCenterIdChange} />);

    const input = screen.getByPlaceholderText(/Search or enter Entity ID/i);
    fireEvent.change(input, { target: { value: 'ENT_TARGET_XYZ' } });

    const expandBtn = screen.getByRole('button', { name: /Expand/i });
    fireEvent.click(expandBtn);

    expect(onCenterIdChange).toHaveBeenCalledWith('ENT_TARGET_XYZ');
  });

  it('binds cytoscape tap event and calls onSelectEntity on node selection', async () => {
    const onSelectEntity = vi.fn();
    render(<NetworkCanvas centerId="ENT_TEST_1" onSelectEntity={onSelectEntity} />);

    const expandBtn = screen.getByRole('button', { name: /Expand/i });
    fireEvent.click(expandBtn);

    // Give cytoscape instantiation a cycle
    await vi.waitFor(() => {
      expect(mockCyInstance).toBeDefined();
      expect(mockCyInstance.on).toHaveBeenCalledWith('tap', 'node', expect.any(Function));
    });

    // Simulate cytoscape tap event
    const tapHandler = mockCyInstance.on.mock.calls.find((call) => call[0] === 'tap' && call[1] === 'node')?.[2];
    expect(tapHandler).toBeDefined();

    const mockEvent = {
      target: {
        data: () => ({ id: 'ENT_TEST_1', type: 'Entity', label: 'Cluster Alpha' }),
      },
    };
    tapHandler(mockEvent);

    expect(onSelectEntity).toHaveBeenCalledWith('ENT_TEST_1', expect.objectContaining({ id: 'ENT_TEST_1' }));
  });
});
