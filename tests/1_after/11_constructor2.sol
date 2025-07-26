// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract Escrow {
    constructor(
        address           _owner,
        address   memory  _signer,
        address[] memory  _whitelistedTokens,
        uint      storage _feeOnClaim,
        uint              _batchLimit
    )  {
        // do things
    }
}