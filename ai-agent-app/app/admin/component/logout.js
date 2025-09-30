"use client";

export function LogoutButton() {
  const onClick = async () => {
    await fetch(process.env.NEXT_PUBLIC_API_URL + "/auth/logout", {
      method: "POST",
      credentials: "include",
    });
    window.location.href = "/admin/login";
  };

  const buttonStyle = {
    padding: "8px 16px",
    borderRadius: "6px",
    border: "1px solid #c53030",
    backgroundColor: "#e53e3e",
    color: "#fff",
    fontWeight: "bold",
    cursor: "pointer",
  };

  const hoverStyle = {
    backgroundColor: "#c53030",
  };

  return (
    <button
      onClick={onClick}
      style={buttonStyle}
      onMouseOver={(e) => (e.currentTarget.style.backgroundColor = hoverStyle.backgroundColor)}
      onMouseOut={(e) => (e.currentTarget.style.backgroundColor = buttonStyle.backgroundColor)}
    >
      Logout
    </button>
  );
}
