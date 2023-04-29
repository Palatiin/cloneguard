import React from 'react';
import { NavLink } from 'react-router-dom';

function NavigationMenu() {
    return (
        <nav>
            <ul>
                <li>
                    <NavLink exact to="/" activeClassName="active">Overview</NavLink>
                </li>
                <li>
                    <NavLink to="/prepare" activeClassName="active">Prepare detection</NavLink>
                </li>
                <li>
                    <NavLink to="/results" activeClassName="active">Detection results</NavLink>
                </li>
            </ul>
        </nav>
    );
}

export default NavigationMenu;
