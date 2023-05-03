import React from 'react';
import NavigationMenu from './NavigationMenu';

function Header() {
    return (
        <header>
            <div className="branding">
                { /* <div className="logo">Your Logo</div> */ }
                <div className="site-title">Detection of Cloned Vulnerabilities</div>
            </div>
            <NavigationMenu />
        </header>
    );
}

export default Header;
