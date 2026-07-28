import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CartProvider from "../Provider/CartProvider";
import { useCart } from "../context/CartContext";

const TestConsumer = () => {
  const { state, dispatch } = useCart();
  return (
    <div>
      <span data-testid="loading">{String(state.loading)}</span>
      <span data-testid="total">{state.total}</span>
      <span data-testid="itemCount">{state.itemCount}</span>
      <span data-testid="items-length">{state.items.length}</span>
      <button
        data-testid="start-loading"
        onClick={() => dispatch({ type: "START_LOADING" })}
      >
        Start
      </button>
      <button
        data-testid="stop-loading"
        onClick={() => dispatch({ type: "STOP_LOADING" })}
      >
        Stop
      </button>
      <button
        data-testid="set-cart"
        onClick={() =>
          dispatch({
            type: "SET_CART",
            payload: {
              items: [{ id: 1, name: "Test" }],
              subtotal: 100,
              total: 110,
              itemCount: 1,
            },
          })
        }
      >
        Set Cart
      </button>
    </div>
  );
};

describe("CartProvider", () => {
  it("provides default state", () => {
    render(
      <CartProvider>
        <TestConsumer />
      </CartProvider>
    );
    expect(screen.getByTestId("loading")).toHaveTextContent("false");
    expect(screen.getByTestId("total")).toHaveTextContent("0");
    expect(screen.getByTestId("itemCount")).toHaveTextContent("0");
    expect(screen.getByTestId("items-length")).toHaveTextContent("0");
  });

  it("handles START_LOADING action", async () => {
    const user = userEvent.setup();
    render(
      <CartProvider>
        <TestConsumer />
      </CartProvider>
    );
    await user.click(screen.getByTestId("start-loading"));
    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("true");
    });
  });

  it("handles STOP_LOADING action", async () => {
    const user = userEvent.setup();
    render(
      <CartProvider>
        <TestConsumer />
      </CartProvider>
    );
    await user.click(screen.getByTestId("start-loading"));
    await user.click(screen.getByTestId("stop-loading"));
    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });
  });

  it("handles SET_CART action", async () => {
    const user = userEvent.setup();
    render(
      <CartProvider>
        <TestConsumer />
      </CartProvider>
    );
    await user.click(screen.getByTestId("set-cart"));
    await waitFor(() => {
      expect(screen.getByTestId("total")).toHaveTextContent("110");
    });
    expect(screen.getByTestId("itemCount")).toHaveTextContent("1");
    expect(screen.getByTestId("items-length")).toHaveTextContent("1");
    expect(screen.getByTestId("loading")).toHaveTextContent("false");
  });
});
