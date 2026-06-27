import React from 'react';
import styles from './Navbar.module.css';

export default function Navbar() {
  return (
    <nav className={styles.navbar}>
      <h1 className={styles.navbarTitle}>David van Vliet</h1>
      <p className={styles.navbarSubtitle}>22; New York City; david@theradarcorp.com</p>
    </nav>
  );
}
