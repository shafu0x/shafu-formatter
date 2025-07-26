// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract Escrow {
    function fund()  {
        distributions[distributionId] = Distribution({
            amount:        distribution.amount,
            token:         distribution.token,
            recipient:     distribution.recipient,
            claimDeadline: block.timestamp + distribution.claimPeriod,
            status:        DistributionStatus.Distributed,
            exists:        true,
            _type:         _type,
            payer:         _type == DistributionType.Solo ? msg.sender : address(0),
            fee:           feeOnClaim
        });
        // do things
    }
}