// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract Escrow {
    constructor(
        address          _owner,
        address          _signer,
        address[] memory _whitelistedTokens,
        uint             _feeOnClaim,
        uint             _batchLimit
    )  {
        // do things
    }
}