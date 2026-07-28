import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import QuantitySelector from "../components/QuantitySelector";

describe("QuantitySelector", () => {
  it("renders with initial quantity", () => {
    render(
      <QuantitySelector quantity={3} onQuantityChange={() => {}} />
    );
    const input = screen.getByRole("spinbutton");
    expect(input).toHaveValue(3);
  });

  it("calls onQuantityChange with decremented value on minus click", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <QuantitySelector quantity={5} onQuantityChange={onChange} />
    );
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[0]);
    expect(onChange).toHaveBeenCalledWith(4);
  });

  it("calls onQuantityChange with incremented value on plus click", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <QuantitySelector quantity={5} onQuantityChange={onChange} />
    );
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]);
    expect(onChange).toHaveBeenCalledWith(6);
  });

  it("disables decrement button at 0", () => {
    render(
      <QuantitySelector quantity={0} onQuantityChange={() => {}} />
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toBeDisabled();
  });

  it("disables increment button at max", () => {
    render(
      <QuantitySelector quantity={99} onQuantityChange={() => {}} max={99} />
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons[1]).toBeDisabled();
  });

  it("handles manual input change", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <QuantitySelector quantity={5} onQuantityChange={onChange} />
    );
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "7");
    expect(onChange).toHaveBeenCalled();
  });

  it("clamps manual input to max", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <QuantitySelector quantity={5} onQuantityChange={onChange} max={10} />
    );
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "99");
    expect(onChange).toHaveBeenCalledWith(10);
  });
});
